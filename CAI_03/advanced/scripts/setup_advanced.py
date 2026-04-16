"""
setup_advanced.py
-----------------
Provisions all AWS resources required for CAI_03/advanced:

  1. IAM Lambda execution role (transcribe, translate, polly, s3, logs)
  2. Lambda function: multilingual-audio-handler
  3. S3 event notification: audio_inputs/*.mp3 → Lambda
  4. CI IAM user for GitHub Actions (s3:PutObject)

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_03/advanced/scripts/setup_advanced.py

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

S3_BUCKET        = os.environ.get("S3_BUCKET")
AWS_REGION       = os.environ.get("AWS_REGION", "us-east-1")
TARGET_LANG      = os.environ.get("TARGET_LANG", "es")
LAMBDA_ROLE_NAME = "MultilingualLambdaExecutionRole"
FUNCTION_NAME    = "multilingual-audio-handler"
CI_USERNAME      = "multilingual-advanced-ci-user"
CI_POLICY_NAME   = "MultilingualAdvancedCIPolicy"
HANDLER_PATH     = Path(__file__).parent.parent / "lambda" / "handler.py"

if not S3_BUCKET:
    print("Error: S3_BUCKET environment variable is required.")
    sys.exit(1)

iam = boto3.client("iam",    region_name=AWS_REGION)
lam = boto3.client("lambda", region_name=AWS_REGION)
s3  = boto3.client("s3",     region_name=AWS_REGION)
sts = boto3.client("sts",    region_name=AWS_REGION)
account = sts.get_caller_identity()["Account"]


def get_or_create_role() -> str:
    try:
        role = iam.get_role(RoleName=LAMBDA_ROLE_NAME)
        print(f"Lambda role '{LAMBDA_ROLE_NAME}' already exists.")
        return role["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    assume = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
    role_arn = iam.create_role(RoleName=LAMBDA_ROLE_NAME, AssumeRolePolicyDocument=json.dumps(assume))["Role"]["Arn"]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": "*"},
            {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
            {"Effect": "Allow", "Action": ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"], "Resource": "*"},
            {"Effect": "Allow", "Action": "translate:TranslateText", "Resource": "*"},
            {"Effect": "Allow", "Action": "polly:SynthesizeSpeech",  "Resource": "*"},
        ],
    }
    iam.put_role_policy(RoleName=LAMBDA_ROLE_NAME, PolicyName="MultilingualLambdaPolicy", PolicyDocument=json.dumps(policy))
    print(f"Created Lambda role: {LAMBDA_ROLE_NAME}")
    print("  Waiting 10s for IAM role to propagate...")
    time.sleep(10)
    return role_arn


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(HANDLER_PATH, "handler.py")
    return buf.getvalue()


def get_or_create_lambda(role_arn: str) -> str:
    zip_bytes = build_zip()
    try:
        fn = lam.get_function(FunctionName=FUNCTION_NAME)
        print(f"Lambda '{FUNCTION_NAME}' exists, updating code...")
        lam.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
        lam.get_waiter("function_updated").wait(FunctionName=FUNCTION_NAME)
        return fn["Configuration"]["FunctionArn"]
    except lam.exceptions.ResourceNotFoundException:
        pass

    fn_arn = lam.create_function(
        FunctionName=FUNCTION_NAME,
        Runtime="python3.11",
        Role=role_arn,
        Handler="handler.lambda_handler",
        Code={"ZipFile": zip_bytes},
        Timeout=300,  # Transcribe jobs can take time
        Environment={"Variables": {"TARGET_LANG": TARGET_LANG, "AWS_REGION": AWS_REGION}},
    )["FunctionArn"]
    lam.get_waiter("function_active").wait(FunctionName=FUNCTION_NAME)
    print(f"Created Lambda: {FUNCTION_NAME}")
    return fn_arn


def configure_s3_notification(fn_arn: str):
    try:
        lam.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId="s3-invoke-audio",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{S3_BUCKET}",
        )
    except lam.exceptions.ResourceConflictException:
        pass

    s3.put_bucket_notification_configuration(
        Bucket=S3_BUCKET,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [{
                "Id": "MultilingualAudioTrigger",
                "LambdaFunctionArn": fn_arn,
                "Events": ["s3:ObjectCreated:*"],
                "Filter": {"Key": {"FilterRules": [
                    {"Name": "prefix", "Value": "audio_inputs/"},
                    {"Name": "suffix", "Value": ".mp3"},
                ]}},
            }]
        },
    )
    print(f"Configured S3 trigger: audio_inputs/*.mp3 → {FUNCTION_NAME}")


def create_ci_user(fn_arn: str):
    try:
        iam.create_user(UserName=CI_USERNAME)
        print(f"Created CI user: {CI_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"CI user '{CI_USERNAME}' already exists, continuing...")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": "s3:PutObject", "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
            {"Effect": "Allow", "Action": ["lambda:UpdateFunctionCode", "lambda:GetFunction"], "Resource": fn_arn},
        ],
    }
    iam.put_user_policy(UserName=CI_USERNAME, PolicyName=CI_POLICY_NAME, PolicyDocument=json.dumps(policy))

    for key in iam.list_access_keys(UserName=CI_USERNAME)["AccessKeyMetadata"]:
        iam.delete_access_key(UserName=CI_USERNAME, AccessKeyId=key["AccessKeyId"])
    key = iam.create_access_key(UserName=CI_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up CAI_03/advanced...")
    print(f"  Bucket: {S3_BUCKET} | Region: {AWS_REGION} | Lang: {TARGET_LANG}\n")

    role_arn = get_or_create_role()
    fn_arn   = get_or_create_lambda(role_arn)
    configure_s3_notification(fn_arn)
    access_key_id, secret = create_ci_user(fn_arn)

    print(f"\n{'─' * 55}")
    print("Success. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET             = {S3_BUCKET}")
    print(f"\nLambda ARN (save for complex tier):")
    print(f"  LAMBDA_ARN            = {fn_arn}")
    print(f"\nStore the secret key securely — it will not be shown again.")
