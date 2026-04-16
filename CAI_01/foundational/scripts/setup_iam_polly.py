"""
setup_iam_polly.py — creates an IAM user with least-privilege permissions for the Polly pipeline.

Permissions granted:
  - polly:SynthesizeSpeech
  - s3:PutObject scoped to S3_BUCKET_NAME

Prints the access key credentials to add as GitHub Actions secrets.

Usage:
  export S3_BUCKET_NAME=cai-01-jossai-1
  export AWS_REGION=us-east-1
  python3 setup_iam_polly.py
"""

import boto3
import json
import os
import sys

# Config — read from environment variables
S3_BUCKET    = os.environ.get("S3_BUCKET_NAME")
IAM_USERNAME = os.environ.get("IAM_USERNAME", "polly-pipeline-user")
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-1")
POLICY_NAME  = "PollyPipelinePolicy"

if not S3_BUCKET:
    print("Error: S3_BUCKET_NAME environment variable is required.")
    sys.exit(1)

iam = boto3.client("iam", region_name=AWS_REGION)

# IAM policy — only the two permissions this pipeline actually needs
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowPollySynthesize",
            "Effect": "Allow",
            "Action": "polly:SynthesizeSpeech",
            "Resource": "*",  # Polly doesn't support resource-level scoping
        },
        {
            "Sid": "AllowS3PutObject",
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": f"arn:aws:s3:::{S3_BUCKET}/*",  # Scoped to this bucket only
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
    # put_user_policy creates or replaces the policy — safe to re-run
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
    print(f"\nSetting up IAM user for the Polly pipeline...")
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
    print(f"\n⚠️  Store the secret key securely — it will not be shown again.")
