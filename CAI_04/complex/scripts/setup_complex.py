"""
setup_complex.py
----------------
Deploys the CAI_04/complex infrastructure using CloudFormation.

  1. Deploys prompt-pipeline-beta-stack (Env=beta)
  2. Deploys prompt-pipeline-prod-stack (Env=prod)
  3. Deploys handler.py code to both Lambda functions
  4. Configures S3 event notifications: prompt_inputs/*.json → Lambda
  5. Uploads prompt templates to S3
  6. Creates a CI IAM user for GitHub Actions

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_04/complex/scripts/setup_complex.py

Required env vars:
  S3_BUCKET_BETA  — beta S3 bucket
  S3_BUCKET_PROD  — prod S3 bucket
  AWS_REGION      — defaults to us-east-1
"""

import boto3
import io
import json
import os
import sys
import zipfile
from pathlib import Path

S3_BUCKET_BETA = os.environ.get("S3_BUCKET_BETA")
S3_BUCKET_PROD = os.environ.get("S3_BUCKET_PROD")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
TEMPLATE_PATH  = Path(__file__).parent.parent / "cloudformation" / "template.yml"
HANDLER_PATH   = Path(__file__).parent.parent / "lambda" / "handler.py"
TEMPLATES_DIR  = Path(__file__).parent.parent.parent / "foundational" / "prompt_templates"
CI_USERNAME    = "prompt-pipeline-complex-ci-user"
CI_POLICY_NAME = "PromptPipelineComplexCIPolicy"
STACKS = {
    "beta": {"stack": "prompt-pipeline-beta-stack", "bucket": None},
    "prod": {"stack": "prompt-pipeline-prod-stack", "bucket": None},
}

if not S3_BUCKET_BETA or not S3_BUCKET_PROD:
    print("Error: S3_BUCKET_BETA and S3_BUCKET_PROD environment variables are required.")
    sys.exit(1)

STACKS["beta"]["bucket"] = S3_BUCKET_BETA
STACKS["prod"]["bucket"] = S3_BUCKET_PROD

cfn = boto3.client("cloudformation", region_name=AWS_REGION)
lam = boto3.client("lambda",         region_name=AWS_REGION)
iam = boto3.client("iam",            region_name=AWS_REGION)
s3  = boto3.client("s3",             region_name=AWS_REGION)
sts = boto3.client("sts",            region_name=AWS_REGION)
account = sts.get_caller_identity()["Account"]


def deploy_stack(env: str, stack_name: str, bucket: str):
    template_body = TEMPLATE_PATH.read_text()
    params = [
        {"ParameterKey": "Env",          "ParameterValue": env},
        {"ParameterKey": "S3BucketName", "ParameterValue": bucket},
    ]
    caps = ["CAPABILITY_NAMED_IAM"]
    try:
        cfn.describe_stacks(StackName=stack_name)
        print(f"Updating stack '{stack_name}'...")
        try:
            cfn.update_stack(StackName=stack_name, TemplateBody=template_body, Parameters=params, Capabilities=caps)
            cfn.get_waiter("stack_update_complete").wait(StackName=stack_name)
        except cfn.exceptions.ClientError as e:
            if "No updates are to be performed" in str(e):
                print(f"  No changes.")
                return
            raise
    except cfn.exceptions.ClientError:
        print(f"Creating stack '{stack_name}'...")
        cfn.create_stack(StackName=stack_name, TemplateBody=template_body, Parameters=params, Capabilities=caps)
        cfn.get_waiter("stack_create_complete").wait(StackName=stack_name)
    print(f"  Stack '{stack_name}' deployed.")


def get_stack_output(stack_name: str, key: str) -> str:
    resp = cfn.describe_stacks(StackName=stack_name)
    for o in resp["Stacks"][0].get("Outputs", []):
        if o["OutputKey"] == key:
            return o["OutputValue"]
    return ""


def deploy_lambda_code(fn_name: str):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(HANDLER_PATH, "handler.py")
    lam.update_function_code(FunctionName=fn_name, ZipFile=buf.getvalue())
    lam.get_waiter("function_updated").wait(FunctionName=fn_name)
    print(f"  Deployed code to {fn_name}")


def configure_s3_notifications(env: str, fn_arn: str, bucket: str):
    fn_name = f"prompt-pipeline-{env}-handler"
    try:
        lam.add_permission(
            FunctionName=fn_name, StatementId=f"s3-invoke-{env}",
            Action="lambda:InvokeFunction", Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{bucket}",
        )
    except lam.exceptions.ResourceConflictException:
        pass

    s3.put_bucket_notification_configuration(
        Bucket=bucket,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [{
                "Id": f"PromptPipelineTrigger{env.capitalize()}",
                "LambdaFunctionArn": fn_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {"Key": {"FilterRules": [
                    {"Name": "prefix", "Value": "prompt_inputs/"},
                    {"Name": "suffix", "Value": ".json"},
                ]}},
            }]
        },
    )
    print(f"  S3 trigger configured on {bucket}")


def upload_templates(bucket: str):
    if not TEMPLATES_DIR.exists():
        return
    for f in TEMPLATES_DIR.glob("*.txt"):
        key = f"prompt_templates/{f.name}"
        s3.upload_file(str(f), bucket, key, ExtraArgs={"ContentType": "text/plain"})
        print(f"  Uploaded template to {bucket}: {key}")


def create_ci_user(fn_arns: dict):
    try:
        iam.create_user(UserName=CI_USERNAME)
        print(f"Created CI user: {CI_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"CI user '{CI_USERNAME}' already exists, continuing...")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["cloudformation:CreateStack", "cloudformation:UpdateStack", "cloudformation:DescribeStacks"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["iam:CreateRole", "iam:PutRolePolicy", "iam:GetRole", "iam:PassRole"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["lambda:UpdateFunctionCode", "lambda:GetFunction", "lambda:CreateFunction"], "Resource": list(fn_arns.values())},
            {"Effect": "Allow", "Action": "s3:PutObject", "Resource": [f"arn:aws:s3:::{S3_BUCKET_BETA}/*", f"arn:aws:s3:::{S3_BUCKET_PROD}/*"]},
        ],
    }
    iam.put_user_policy(UserName=CI_USERNAME, PolicyName=CI_POLICY_NAME, PolicyDocument=json.dumps(policy))

    for key in iam.list_access_keys(UserName=CI_USERNAME)["AccessKeyMetadata"]:
        iam.delete_access_key(UserName=CI_USERNAME, AccessKeyId=key["AccessKeyId"])
    key = iam.create_access_key(UserName=CI_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nDeploying CAI_04/complex via CloudFormation...")
    print(f"  Beta bucket: {S3_BUCKET_BETA}")
    print(f"  Prod bucket: {S3_BUCKET_PROD}")
    print(f"  Region:      {AWS_REGION}\n")

    fn_arns = {}
    for env, cfg in STACKS.items():
        print(f"── {env.upper()} ──────────────────────────")
        deploy_stack(env, cfg["stack"], cfg["bucket"])
        fn_name = f"prompt-pipeline-{env}-handler"
        deploy_lambda_code(fn_name)
        fn_arns[env] = get_stack_output(cfg["stack"], "LambdaArn")
        configure_s3_notifications(env, fn_arns[env], cfg["bucket"])
        upload_templates(cfg["bucket"])
        print()

    print("Creating CI IAM user...")
    access_key_id, secret = create_ci_user(fn_arns)

    print(f"\n{'─' * 55}")
    print("Success. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET_BETA        = {S3_BUCKET_BETA}")
    print(f"  S3_BUCKET_PROD        = {S3_BUCKET_PROD}")
    print(f"\nStore the secret key securely — it will not be shown again.")
