"""
setup_modern.py
---------------
Provisions all AWS resources required for CAI_02/modern:

  1. DynamoDB tables: beta_results, prod_results (if not already created)
  2. IAM user with permissions for Bedrock, S3, and DynamoDB
  3. Verifies Nova 2 Lite model access in Bedrock

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_02/modern/scripts/setup_modern.py

Required env vars:
  S3_BUCKET   — S3 bucket name (must already exist)
  AWS_REGION  — defaults to us-east-1 (must be a Nova-supported region)
"""

import boto3
import json
import os
import sys

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET    = os.environ.get("S3_BUCKET")
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-1")
IAM_USERNAME = "rekognition-modern-user"
POLICY_NAME  = "RekognitionModernPolicy"
MODEL_ID     = "us.amazon.nova-2-lite-v1:0"
TABLES       = ["beta_results", "prod_results"]
NOVA_REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
# ─────────────────────────────────────────────────────────────────────────────

if not S3_BUCKET:
    print("Error: S3_BUCKET environment variable is required.")
    sys.exit(1)

if AWS_REGION not in NOVA_REGIONS:
    print(f"Warning: Nova 2 Lite is only available in {NOVA_REGIONS}")
    print(f"  Your region '{AWS_REGION}' may not work.")

iam     = boto3.client("iam",              region_name=AWS_REGION)
dynamo  = boto3.client("dynamodb",         region_name=AWS_REGION)
bedrock = boto3.client("bedrock",          region_name=AWS_REGION)
sts     = boto3.client("sts",              region_name=AWS_REGION)
account = sts.get_caller_identity()["Account"]


def check_bedrock_model_access():
    print("Checking Nova 2 Lite model access...")
    try:
        models = bedrock.list_foundation_models(byProvider="Amazon")["modelSummaries"]
        nova = next((m for m in models if "nova-2-lite" in m.get("modelId", "").lower()), None)
        if nova:
            status = nova.get("modelLifecycle", {}).get("status", "unknown")
            print(f"  Nova 2 Lite found — status: {status}")
            if status != "ACTIVE":
                print("  Warning: model may not be active. Enable it in Bedrock Console → Model access.")
        else:
            print("  Nova 2 Lite not found in model list.")
            print("  Go to Bedrock Console → Model access → enable 'Amazon Nova Lite'")
    except Exception as e:
        print(f"  Could not check model access: {e}")
        print("  Manually verify in Bedrock Console → Model access → Amazon Nova Lite")


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


def create_iam_user():
    try:
        iam.create_user(UserName=IAM_USERNAME)
        print(f"Created IAM user: {IAM_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM user '{IAM_USERNAME}' already exists, continuing...")

    table_arns = [f"arn:aws:dynamodb:{AWS_REGION}:{account}:table/{t}" for t in TABLES]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowBedrockNova",
                "Effect": "Allow",
                "Action": "bedrock:InvokeModel",
                "Resource": f"arn:aws:bedrock:{AWS_REGION}::foundation-model/amazon.nova-lite-v1:0",
            },
            {
                "Sid": "AllowS3",
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:GetObject"],
                "Resource": f"arn:aws:s3:::{S3_BUCKET}/*",
            },
            {
                "Sid": "AllowDynamoWrite",
                "Effect": "Allow",
                "Action": "dynamodb:PutItem",
                "Resource": table_arns,
            },
        ],
    }

    iam.put_user_policy(UserName=IAM_USERNAME, PolicyName=POLICY_NAME, PolicyDocument=json.dumps(policy))
    print(f"Attached policy '{POLICY_NAME}'")
    print(f"  - bedrock:InvokeModel on Nova 2 Lite")
    print(f"  - s3:PutObject + s3:GetObject on {S3_BUCKET}")
    print(f"  - dynamodb:PutItem on {TABLES}")


def create_access_key():
    existing = iam.list_access_keys(UserName=IAM_USERNAME)["AccessKeyMetadata"]
    for key in existing:
        iam.delete_access_key(UserName=IAM_USERNAME, AccessKeyId=key["AccessKeyId"])
        print(f"Deleted old access key: {key['AccessKeyId']}")
    key = iam.create_access_key(UserName=IAM_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up CAI_02/modern (Nova 2 Lite)...")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Region: {AWS_REGION}\n")

    check_bedrock_model_access()
    create_dynamodb_tables()
    create_iam_user()
    access_key_id, secret = create_access_key()

    print(f"\nSuccess. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET             = {S3_BUCKET}")
    print(f"  DYNAMODB_TABLE_BETA   = beta_results")
    print(f"  DYNAMODB_TABLE_PROD   = prod_results")
    print(f"\nRun locally:")
    print(f"  S3_BUCKET={S3_BUCKET} DYNAMODB_TABLE=beta_results BRANCH=my-branch \\")
    print(f"  AWS_REGION={AWS_REGION} /tmp/cai01-venv/bin/python CAI_02/modern/analyze_image.py")
    print(f"\nStore the secret key securely — it will not be shown again.")
