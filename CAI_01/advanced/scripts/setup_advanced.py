"""
setup_advanced.py — provisions all AWS infrastructure for the advanced Polly pipeline.

Run this ONCE before using GitHub Actions. Creates:
  1. IAM execution role (Polly + S3 + CloudWatch)
  2. Lambda: PollyTextToSpeech_Beta  (ENVIRONMENT=beta)
  3. Lambda: PollyTextToSpeech_Prod  (ENVIRONMENT=prod)
  4. API Gateway with POST /synthesize for each Lambda

Prints the two API Gateway URLs to add as GitHub Secrets.

Usage:
  export S3_BUCKET_NAME=cai-01-jossai-1
  export AWS_REGION=us-east-1
  python3 setup_advanced.py

Safe to re-run — updates existing resources instead of failing.
"""

import boto3
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

# Config
S3_BUCKET    = os.environ.get("S3_BUCKET_NAME")
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-1")
ROLE_NAME    = "PollyLambdaExecutionRole"
HANDLER_PATH = Path(__file__).parent.parent / "lambda" / "handler.py"
FUNCTIONS    = {
    "beta": "PollyTextToSpeech_Beta",
    "prod": "PollyTextToSpeech_Prod",
}

if not S3_BUCKET:
    print("Error: S3_BUCKET_NAME environment variable is required.")
    sys.exit(1)

iam     = boto3.client("iam",        region_name=AWS_REGION)
lam     = boto3.client("lambda",     region_name=AWS_REGION)
apigw   = boto3.client("apigateway", region_name=AWS_REGION)
account = boto3.client("sts").get_caller_identity()["Account"]


def get_or_create_role() -> str:
    """Get or create the Lambda execution role. Returns the role ARN."""
    try:
        role = iam.get_role(RoleName=ROLE_NAME)
        print(f"IAM role '{ROLE_NAME}' already exists.")
        return role["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    # Trust policy — only Lambda can assume this role
    assume = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }
    role = iam.create_role(RoleName=ROLE_NAME, AssumeRolePolicyDocument=json.dumps(assume), Description="Execution role for Polly Lambda pipeline")
    role_arn = role["Role"]["Arn"]
    print(f"Created IAM role: {ROLE_NAME}")

    # Permissions — Polly, S3 (scoped to bucket), CloudWatch Logs
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Sid": "AllowPolly",  "Effect": "Allow", "Action": "polly:SynthesizeSpeech", "Resource": "*"},
            {"Sid": "AllowS3Put",  "Effect": "Allow", "Action": "s3:PutObject", "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
            {"Sid": "AllowLogs",   "Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
        ],
    }
    iam.put_role_policy(RoleName=ROLE_NAME, PolicyName="PollyLambdaPolicy", PolicyDocument=json.dumps(policy))
    print("  Attached inline policy (polly, s3, logs)")

    # IAM changes take a few seconds to propagate before Lambda can use the role
    print("  Waiting 10s for IAM role to propagate...")
    time.sleep(10)
    return role_arn


def build_zip() -> bytes:
    """Package handler.py into a zip in memory — Lambda requires code as a zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(HANDLER_PATH, "handler.py")
    return buf.getvalue()


def get_or_create_lambda(name: str, env: str, role_arn: str, zip_bytes: bytes) -> str:
    """Create or update a Lambda function. Returns the function ARN."""
    try:
        fn = lam.get_function(FunctionName=name)
        print(f"Lambda '{name}' already exists, updating code...")
        lam.update_function_code(FunctionName=name, ZipFile=zip_bytes)
        lam.get_waiter("function_updated").wait(FunctionName=name)
        return fn["Configuration"]["FunctionArn"]
    except lam.exceptions.ResourceNotFoundException:
        pass

    response = lam.create_function(
        FunctionName=name,
        Runtime="python3.11",
        Role=role_arn,
        Handler="handler.lambda_handler",  # filename.function_name
        Code={"ZipFile": zip_bytes},
        Timeout=30,
        Environment={"Variables": {"ENVIRONMENT": env, "S3_BUCKET_NAME": S3_BUCKET}},
    )
    print(f"Created Lambda: {name}")
    lam.get_waiter("function_active").wait(FunctionName=name)
    return response["FunctionArn"]


def create_api_gateway(env: str, function_arn: str, function_name: str) -> str:
    """Create (or reuse) an API Gateway with POST /synthesize → Lambda. Returns the endpoint URL."""
    api_name = f"PollyAPI_{env.capitalize()}"

    apis = apigw.get_rest_apis()["items"]
    existing = next((a for a in apis if a["name"] == api_name), None)
    if existing:
        api_id = existing["id"]
        print(f"API Gateway '{api_name}' already exists (id: {api_id})")
    else:
        api_id = apigw.create_rest_api(name=api_name)["id"]
        print(f"Created API Gateway: {api_name} (id: {api_id})")

    resources   = apigw.get_resources(restApiId=api_id)["items"]
    root_id     = next(r for r in resources if r["path"] == "/")["id"]
    existing_res = next((r for r in resources if r.get("pathPart") == "synthesize"), None)
    resource_id = existing_res["id"] if existing_res else apigw.create_resource(restApiId=api_id, parentId=root_id, pathPart="synthesize")["id"]

    # Add POST method (skip if already exists)
    try:
        apigw.put_method(restApiId=api_id, resourceId=resource_id, httpMethod="POST", authorizationType="NONE")
    except apigw.exceptions.ConflictException:
        pass

    # Wire POST → Lambda via AWS_PROXY integration
    lambda_uri = f"arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{function_arn}/invocations"
    apigw.put_integration(restApiId=api_id, resourceId=resource_id, httpMethod="POST", type="AWS_PROXY", integrationHttpMethod="POST", uri=lambda_uri)

    # Grant API Gateway permission to invoke this Lambda
    try:
        lam.add_permission(
            FunctionName=function_name,
            StatementId=f"apigateway-{env}-invoke",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{AWS_REGION}:{account}:{api_id}/*/POST/synthesize",
        )
    except lam.exceptions.ResourceConflictException:
        pass

    apigw.create_deployment(restApiId=api_id, stageName=env)
    print(f"  Deployed to stage: {env}")

    return f"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/{env}/synthesize"


if __name__ == "__main__":
    print(f"\nSetting up advanced infrastructure...")
    print(f"  Bucket: {S3_BUCKET}  |  Region: {AWS_REGION}\n")

    role_arn  = get_or_create_role()
    zip_bytes = build_zip()
    endpoints = {}

    for env, name in FUNCTIONS.items():
        print(f"\n── {env.upper()} ──────────────────────────")
        fn_arn         = get_or_create_lambda(name, env, role_arn, zip_bytes)
        url            = create_api_gateway(env, fn_arn, name)
        endpoints[env] = url
        print(f"  Endpoint: {url}")

    print(f"\n{'─' * 55}")
    print(f"Done! Add these as GitHub Actions secrets:")
    print(f"  https://github.com/jossai87/awsai01/settings/secrets/actions\n")
    print(f"  BETA_API_ENDPOINT = {endpoints['beta'].replace('/synthesize', '')}")
    print(f"  PROD_API_ENDPOINT = {endpoints['prod'].replace('/synthesize', '')}")
    print(f"\nTest the endpoints:")
    for env, url in endpoints.items():
        print(f"  curl -X POST {url} -H 'Content-Type: application/json' -d '{{\"text\": \"Hello from {env}\"}}'")
