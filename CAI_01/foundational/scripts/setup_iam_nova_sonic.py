"""
setup_iam_nova_sonic.py — creates an IAM user with least-privilege permissions for the Nova 2 Sonic pipeline.

Permissions granted:
  - bedrock:InvokeModelWithBidirectionalStream (scoped to Nova 2 Sonic model ARN)
  - s3:PutObject scoped to S3_BUCKET_NAME

Note: IAM permissions alone aren't enough for Bedrock — you also need to enable
model access in the console: Bedrock → Model access → Amazon Nova 2 Sonic

Usage:
  export S3_BUCKET_NAME=cai-01-jossai-1
  export AWS_REGION=us-east-1
  python3 setup_iam_nova_sonic.py
"""

import boto3
import json
import os
import sys

# Config
S3_BUCKET      = os.environ.get("S3_BUCKET_NAME")
IAM_USERNAME   = os.environ.get("IAM_USERNAME", "nova-sonic-pipeline-user")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
POLICY_NAME    = "NovaSonicPipelinePolicy"
NOVA_SONIC_ARN = "arn:aws:bedrock:*::foundation-model/amazon.nova-2-sonic-v1:0"

if not S3_BUCKET:
    print("Error: S3_BUCKET_NAME environment variable is required.")
    sys.exit(1)

iam = boto3.client("iam", region_name=AWS_REGION)

# IAM policy — scoped to Nova 2 Sonic model and this bucket only
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowNovaSonicBidirectionalStream",
            "Effect": "Allow",
            "Action": "bedrock:InvokeModelWithBidirectionalStream",
            "Resource": NOVA_SONIC_ARN,
        },
        {
            "Sid": "AllowS3PutObject",
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": f"arn:aws:s3:::{S3_BUCKET}/*",
        },
    ],
}


def create_user():
    try:
        iam.create_user(UserName=IAM_USERNAME)
        print(f"Created IAM user: {IAM_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM user '{IAM_USERNAME}' already exists, continuing...")


def attach_inline_policy():
    iam.put_user_policy(
        UserName=IAM_USERNAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(policy_document),
    )
    print(f"Attached policy '{POLICY_NAME}' to {IAM_USERNAME}")


def create_access_key():
    # AWS allows max 2 access keys per user — delete existing ones first
    existing = iam.list_access_keys(UserName=IAM_USERNAME)["AccessKeyMetadata"]
    for key in existing:
        iam.delete_access_key(UserName=IAM_USERNAME, AccessKeyId=key["AccessKeyId"])
        print(f"Deleted old access key: {key['AccessKeyId']}")

    response = iam.create_access_key(UserName=IAM_USERNAME)
    key = response["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up IAM user for the Nova 2 Sonic pipeline...")
    print(f"  User:   {IAM_USERNAME}")
    print(f"  Bucket: {S3_BUCKET}\n")

    create_user()
    attach_inline_policy()
    access_key_id, secret_access_key = create_access_key()

    print(f"\nDone! Add these as GitHub Actions secrets:")
    print(f"  https://github.com/jossai87/awsai01/settings/secrets/actions\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret_access_key}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET_NAME        = {S3_BUCKET}")
    print(f"\n⚠️  Also enable Nova 2 Sonic in: Bedrock console → Model access")
    print(f"⚠️  Store the secret key securely — it will not be shown again.")
