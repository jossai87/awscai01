"""
setup_advanced.py
-----------------
Provisions all AWS resources required for CAI_02/advanced:

  1. DynamoDB tables: beta_results, prod_results (if not already created)
  2. IAM execution role for both Lambda functions
  3. Lambda function: rekognition-beta-handler  (DYNAMODB_TABLE=beta_results)
  4. Lambda function: rekognition-prod-handler  (DYNAMODB_TABLE=prod_results)
  5. S3 event notifications wiring both prefixes to their Lambda functions
  6. IAM user for GitHub Actions (lambda:UpdateFunctionCode + s3:PutObject + dynamodb:Scan)

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_02/advanced/scripts/setup_advanced.py

Required env vars:
  S3_BUCKET   — S3 bucket name (must already exist)
  AWS_REGION  — defaults to us-east-1
"""

import boto3
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET        = os.environ.get("S3_BUCKET")
AWS_REGION       = os.environ.get("AWS_REGION", "us-east-1")
LAMBDA_ROLE_NAME = "RekognitionLambdaExecutionRole"
CI_USERNAME      = "rekognition-advanced-ci-user"
CI_POLICY_NAME   = "RekognitionAdvancedCIPolicy"
TABLES           = ["beta_results", "prod_results"]
BETA_HANDLER     = Path(__file__).parent.parent / "lambda" / "beta_handler.py"
PROD_HANDLER     = Path(__file__).parent.parent / "lambda" / "prod_handler.py"
FUNCTIONS = {
    "beta": {
        "name": "rekognition-beta-handler",
        "handler_path": BETA_HANDLER,
        "handler_fn": "beta_handler.lambda_handler",
        "table": "beta_results",
        "prefix": "rekognition-input/beta/",
    },
    "prod": {
        "name": "rekognition-prod-handler",
        "handler_path": PROD_HANDLER,
        "handler_fn": "prod_handler.lambda_handler",
        "table": "prod_results",
        "prefix": "rekognition-input/prod/",
    },
}
# ─────────────────────────────────────────────────────────────────────────────

if not S3_BUCKET:
    print("Error: S3_BUCKET environment variable is required.")
    sys.exit(1)

iam    = boto3.client("iam",      region_name=AWS_REGION)
lam    = boto3.client("lambda",   region_name=AWS_REGION)
dynamo = boto3.client("dynamodb", region_name=AWS_REGION)
s3     = boto3.client("s3",       region_name=AWS_REGION)
sts    = boto3.client("sts",      region_name=AWS_REGION)
account = sts.get_caller_identity()["Account"]


def create_dynamodb_tables():
    for table_name in TABLES:
        try:
            dynamo.create_table(
                TableName=table_name,
                AttributeDefinitions=[{"AttributeName": "filename", "AttributeType": "S"}],
                KeySchema=[{"AttributeName": "filename", "KeyType": "HASH"}],
                BillingMode="PAY_PER_REQUEST",
            )
            print(f"Created DynamoDB table: {table_name}")
        except dynamo.exceptions.ResourceInUseException:
            print(f"DynamoDB table '{table_name}' already exists.")


def get_or_create_lambda_role() -> str:
    try:
        role = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
        print(f"Lambda execution role '{LAMBDA_ROLE_NAME}' already exists.")
        return role["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    assume = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }
    role_arn = iam.create_role(
        RoleName=LAMBDA_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(assume),
    )["Role"]["Arn"]

    table_arns = [f"arn:aws:dynamodb:{AWS_REGION}:{account}:table/{t}" for t in TABLES]
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
            {"Effect": "Allow", "Action": "s3:GetObject", "Resource": f"arn:aws:s3:::{S3_BUCKET}/rekognition-input/*"},
            {"Effect": "Allow", "Action": "rekognition:DetectLabels", "Resource": "*"},
            {"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": table_arns},
        ],
    }
    iam.put_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyName="RekognitionLambdaPolicy", PolicyDocument=json.dumps(policy))
    print(f"Created Lambda execution role: {LAMBDA_ROLE_NAME}")
    print("  Waiting 10s for IAM role to propagate...")
    time.sleep(10)
    return role_arn


def build_zip(handler_path: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(handler_path, handler_path.name)
    return buf.getvalue()


def get_or_create_lambda(cfg: dict, role_arn: str) -> str:
    name     = cfg["name"]
    zip_bytes = build_zip(cfg["handler_path"])
    try:
        fn = lam.get_function(FunctionName=name)
        print(f"Lambda '{name}' exists, updating code...")
        lam.update_function_code(FunctionName=name, ZipFile=zip_bytes)
        lam.get_waiter("function_updated").wait(FunctionName=name)
        return fn["Configuration"]["FunctionArn"]
    except lam.exceptions.ResourceNotFoundException:
        pass

    fn_arn = lam.create_function(
        FunctionName=name,
        Runtime="python3.11",
        Role=role_arn,
        Handler=cfg["handler_fn"],
        Code={"ZipFile": zip_bytes},
        Timeout=30,
        Environment={"Variables": {"DYNAMODB_TABLE": cfg["table"]}},
    )["FunctionArn"]
    lam.get_waiter("function_active").wait(FunctionName=name)
    print(f"Created Lambda: {name}")
    return fn_arn


def configure_s3_notifications(fn_arns: dict):
    # Grant S3 permission to invoke each Lambda
    for env, fn_arn in fn_arns.items():
        fn_name = FUNCTIONS[env]["name"]
        try:
            lam.add_permission(
                FunctionName=fn_name,
                StatementId=f"s3-invoke-{env}",
                Action="lambda:InvokeFunction",
                Principal="s3.amazonaws.com",
                SourceArn=f"arn:aws:s3:::{S3_BUCKET}",
            )
        except lam.exceptions.ResourceConflictException:
            pass

    configs = []
    for env, fn_arn in fn_arns.items():
        prefix = FUNCTIONS[env]["prefix"]
        for suffix in [".jpg", ".png"]:
            configs.append({
                "Id": f"Rekognition{env.capitalize()}Trigger{suffix.replace('.', '')}",
                "LambdaFunctionArn": fn_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {"Key": {"FilterRules": [
                    {"Name": "prefix", "Value": prefix},
                    {"Name": "suffix", "Value": suffix},
                ]}},
            })

    s3.put_bucket_notification_configuration(
        Bucket=S3_BUCKET,
        NotificationConfiguration={"LambdaFunctionConfigurations": configs},
    )
    print(f"Configured S3 event notifications on bucket: {S3_BUCKET}")


def create_ci_user(fn_arns: dict):
    try:
        iam.create_user(UserName=CI_USERNAME)
        print(f"Created CI IAM user: {CI_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"CI IAM user '{CI_USERNAME}' already exists, continuing...")

    fn_arn_list = list(fn_arns.values())
    table_arns  = [f"arn:aws:dynamodb:{AWS_REGION}:{account}:table/{t}" for t in TABLES]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["lambda:UpdateFunctionCode", "lambda:GetFunction"], "Resource": fn_arn_list},
            {"Effect": "Allow", "Action": "s3:PutObject", "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
            {"Effect": "Allow", "Action": "dynamodb:Scan", "Resource": table_arns},
        ],
    }
    iam.put_user_policy(UserName=CI_USERNAME, PolicyName=CI_POLICY_NAME, PolicyDocument=json.dumps(policy))
    print(f"Attached CI policy to {CI_USERNAME}")

    existing = iam.list_access_keys(UserName=CI_USERNAME)["AccessKeyMetadata"]
    for key in existing:
        iam.delete_access_key(UserName=CI_USERNAME, AccessKeyId=key["AccessKeyId"])
    key = iam.create_access_key(UserName=CI_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up CAI_02/advanced...")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Region: {AWS_REGION}\n")

    create_dynamodb_tables()
    role_arn = get_or_create_lambda_role()

    fn_arns = {}
    for env, cfg in FUNCTIONS.items():
        print(f"\n── {env.upper()} ──────────────────────────")
        fn_arns[env] = get_or_create_lambda(cfg, role_arn)
        print(f"  ARN: {fn_arns[env]}")

    print("\nConfiguring S3 event notifications...")
    configure_s3_notifications(fn_arns)

    print("\nCreating CI IAM user...")
    access_key_id, secret = create_ci_user(fn_arns)

    print(f"\n{'─' * 55}")
    print("Success. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET             = {S3_BUCKET}")
    print(f"  DYNAMODB_TABLE_BETA   = beta_results")
    print(f"  DYNAMODB_TABLE_PROD   = prod_results")
    print(f"\nAlso save these Lambda ARNs as secrets (needed by complex tier):")
    print(f"  BETA_LAMBDA_ARN       = {fn_arns['beta']}")
    print(f"  PROD_LAMBDA_ARN       = {fn_arns['prod']}")
    print(f"\nStore the secret key securely — it will not be shown again.")
