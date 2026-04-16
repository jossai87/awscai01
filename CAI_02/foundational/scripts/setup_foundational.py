"""
setup_foundational.py
---------------------
Provisions all AWS resources required for CAI_02/foundational:

  1. DynamoDB tables: beta_results, prod_results
  2. IAM user with least-privilege permissions:
       - s3:PutObject on your bucket
       - rekognition:DetectLabels
       - dynamodb:PutItem on both tables

On success, prints the access key and secret to use as GitHub Actions secrets.

Usage:
  python CAI_02/foundational/scripts/setup_foundational.py

Required env vars:
  S3_BUCKET   — S3 bucket name (must already exist)
  AWS_REGION  — defaults to us-east-1
"""

import boto3
import json
import os
import sys

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET    = os.environ.get("S3_BUCKET")
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-1")
IAM_USERNAME = "rekognition-foundational-user"
POLICY_NAME  = "RekognitionFoundationalPolicy"
TABLES       = ["beta_results", "prod_results"]
# ─────────────────────────────────────────────────────────────────────────────

if not S3_BUCKET:
    print("Error: S3_BUCKET environment variable is required.")
    sys.exit(1)

iam    = boto3.client("iam",      region_name=AWS_REGION)
dynamo = boto3.client("dynamodb", region_name=AWS_REGION)
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


def create_iam_user():
    try:
        iam.create_user(UserName=IAM_USERNAME)
        print(f"Created IAM user: {IAM_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM user '{IAM_USERNAME}' already exists, continuing...")

    table_arns = [
        f"arn:aws:dynamodb:{AWS_REGION}:{account}:table/{t}" for t in TABLES
    ]

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowS3Put",
                "Effect": "Allow",
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{S3_BUCKET}/*",
            },
            {
                "Sid": "AllowRekognition",
                "Effect": "Allow",
                "Action": "rekognition:DetectLabels",
                "Resource": "*",
            },
            {
                "Sid": "AllowDynamoWrite",
                "Effect": "Allow",
                "Action": "dynamodb:PutItem",
                "Resource": table_arns,
            },
        ],
    }

    iam.put_user_policy(
        UserName=IAM_USERNAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(policy),
    )
    print(f"Attached policy '{POLICY_NAME}'")
    print(f"  - s3:PutObject on {S3_BUCKET}")
    print(f"  - rekognition:DetectLabels")
    print(f"  - dynamodb:PutItem on {TABLES}")


def create_access_key():
    existing = iam.list_access_keys(UserName=IAM_USERNAME)["AccessKeyMetadata"]
    for key in existing:
        iam.delete_access_key(UserName=IAM_USERNAME, AccessKeyId=key["AccessKeyId"])
        print(f"Deleted old access key: {key['AccessKeyId']}")
    key = iam.create_access_key(UserName=IAM_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up CAI_02/foundational...")
    print(f"  Bucket: {S3_BUCKET}")
    print(f"  Region: {AWS_REGION}\n")

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
    print(f"\nStore the secret key securely — it will not be shown again.")
