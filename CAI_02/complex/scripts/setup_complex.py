"""
setup_complex.py
----------------
Deploys the CAI_02/complex infrastructure using CloudFormation.

  1. Deploys rekognition-beta-stack (Env=beta)
  2. Deploys rekognition-prod-stack (Env=prod)
  3. Deploys handler.py code to both Lambda functions
  4. Configures S3 event notifications for both prefixes
  5. Creates a CI IAM user for GitHub Actions

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_02/complex/scripts/setup_complex.py

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
S3_BUCKET      = os.environ.get("S3_BUCKET")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
TEMPLATE_PATH  = Path(__file__).parent.parent / "cloudformation" / "template.yml"
HANDLER_PATH   = Path(__file__).parent.parent / "lambda" / "handler.py"
CI_USERNAME    = "rekognition-complex-ci-user"
CI_POLICY_NAME = "RekognitionComplexCIPolicy"
STACKS = {
    "beta": "rekognition-beta-stack",
    "prod": "rekognition-prod-stack",
}
# ─────────────────────────────────────────────────────────────────────────────

if not S3_BUCKET:
    print("Error: S3_BUCKET environment variable is required.")
    sys.exit(1)

cfn = boto3.client("cloudformation", region_name=AWS_REGION)
lam = boto3.client("lambda",         region_name=AWS_REGION)
iam = boto3.client("iam",            region_name=AWS_REGION)
s3  = boto3.client("s3",             region_name=AWS_REGION)
sts = boto3.client("sts",            region_name=AWS_REGION)
account = sts.get_caller_identity()["Account"]


def deploy_stack(env: str, stack_name: str):
    template_body = TEMPLATE_PATH.read_text()
    params = [
        {"ParameterKey": "Env",          "ParameterValue": env},
        {"ParameterKey": "S3BucketName", "ParameterValue": S3_BUCKET},
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
                print(f"  No changes — already up to date.")
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
    print(f"  Deployed handler code to {fn_name}")


def configure_s3_notifications(beta_arn: str, prod_arn: str):
    for fn_name, fn_arn in [("rekognition-beta-handler", beta_arn), ("rekognition-prod-handler", prod_arn)]:
        try:
            lam.add_permission(
                FunctionName=fn_name,
                StatementId="s3-invoke",
                Action="lambda:InvokeFunction",
                Principal="s3.amazonaws.com",
                SourceArn=f"arn:aws:s3:::{S3_BUCKET}",
            )
        except lam.exceptions.ResourceConflictException:
            pass

    configs = []
    for env, fn_arn in [("beta", beta_arn), ("prod", prod_arn)]:
        prefix = f"rekognition-input/{env}/"
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


def create_ci_user(beta_arn: str, prod_arn: str):
    try:
        iam.create_user(UserName=CI_USERNAME)
        print(f"Created CI IAM user: {CI_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"CI IAM user '{CI_USERNAME}' already exists, continuing...")

    table_arns = [
        f"arn:aws:dynamodb:{AWS_REGION}:{account}:table/beta_results",
        f"arn:aws:dynamodb:{AWS_REGION}:{account}:table/prod_results",
    ]
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["cloudformation:CreateStack", "cloudformation:UpdateStack", "cloudformation:DescribeStacks", "cloudformation:DescribeStackEvents"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["iam:CreateRole", "iam:PutRolePolicy", "iam:GetRole", "iam:PassRole", "iam:AttachRolePolicy"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["lambda:UpdateFunctionCode", "lambda:GetFunction", "lambda:CreateFunction", "lambda:AddPermission"], "Resource": [beta_arn, prod_arn]},
            {"Effect": "Allow", "Action": "s3:PutObject", "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
            {"Effect": "Allow", "Action": "dynamodb:Scan", "Resource": table_arns},
            {"Effect": "Allow", "Action": ["dynamodb:CreateTable", "dynamodb:DescribeTable"], "Resource": table_arns},
        ],
    }
    iam.put_user_policy(UserName=CI_USERNAME, PolicyName=CI_POLICY_NAME, PolicyDocument=json.dumps(policy))

    existing = iam.list_access_keys(UserName=CI_USERNAME)["AccessKeyMetadata"]
    for key in existing:
        iam.delete_access_key(UserName=CI_USERNAME, AccessKeyId=key["AccessKeyId"])
    key = iam.create_access_key(UserName=CI_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nDeploying CAI_02/complex via CloudFormation...")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Region: {AWS_REGION}\n")

    fn_arns = {}
    for env, stack_name in STACKS.items():
        print(f"── {env.upper()} ──────────────────────────")
        deploy_stack(env, stack_name)
        fn_name = f"rekognition-{env}-handler"
        deploy_lambda_code(fn_name)
        fn_arns[env] = get_stack_output(stack_name, "LambdaArn")
        print(f"  Lambda ARN: {fn_arns[env]}\n")

    print("Configuring S3 event notifications...")
    configure_s3_notifications(fn_arns["beta"], fn_arns["prod"])

    print("\nCreating CI IAM user...")
    access_key_id, secret = create_ci_user(fn_arns["beta"], fn_arns["prod"])

    print(f"\n{'─' * 55}")
    print("Success. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET             = {S3_BUCKET}")
    print(f"  DYNAMODB_TABLE_BETA   = beta_results")
    print(f"  DYNAMODB_TABLE_PROD   = prod_results")
    print(f"  BETA_LAMBDA_ARN       = {fn_arns['beta']}")
    print(f"  PROD_LAMBDA_ARN       = {fn_arns['prod']}")
    print(f"\nStore the secret key securely — it will not be shown again.")
