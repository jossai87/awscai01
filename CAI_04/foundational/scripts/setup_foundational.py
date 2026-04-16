"""
setup_foundational.py
---------------------
Provisions all AWS resources required for CAI_04/foundational:

  1. S3 buckets for beta and prod with static website hosting enabled
  2. IAM user with least-privilege permissions:
       - s3:PutObject on both buckets
       - bedrock:InvokeModel on Claude 3 Sonnet

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_04/foundational/scripts/setup_foundational.py

Required env vars:
  S3_BUCKET_BETA  — beta bucket name (will be created)
  S3_BUCKET_PROD  — prod bucket name (will be created)
  AWS_REGION      — defaults to us-east-1
"""

import boto3
import json
import os
import sys

S3_BUCKET_BETA = os.environ.get("S3_BUCKET_BETA")
S3_BUCKET_PROD = os.environ.get("S3_BUCKET_PROD")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
IAM_USERNAME   = "prompt-pipeline-foundational-user"
POLICY_NAME    = "PromptPipelineFoundationalPolicy"
MODEL_ARN      = "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"

if not S3_BUCKET_BETA or not S3_BUCKET_PROD:
    print("Error: S3_BUCKET_BETA and S3_BUCKET_PROD environment variables are required.")
    sys.exit(1)

s3  = boto3.client("s3",  region_name=AWS_REGION)
iam = boto3.client("iam", region_name=AWS_REGION)


def create_bucket(bucket_name: str, env: str):
    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
        print(f"Created S3 bucket: {bucket_name}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket '{bucket_name}' already exists.")
    except Exception as e:
        if "BucketAlreadyExists" in str(e):
            print(f"Bucket '{bucket_name}' already exists.")
        else:
            raise

    # Enable static website hosting
    s3.put_bucket_website(
        Bucket=bucket_name,
        WebsiteConfiguration={
            "IndexDocument": {"Suffix": "index.html"},
            "ErrorDocument": {"Key": "error.html"},
        },
    )

    # Public read policy for static hosting
    public_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*",
        }],
    }
    # Disable block public access first
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(public_policy))
    print(f"  Enabled static website hosting on {bucket_name}")
    print(f"  URL: http://{bucket_name}.s3-website-{AWS_REGION}.amazonaws.com")


def create_iam_user():
    try:
        iam.create_user(UserName=IAM_USERNAME)
        print(f"Created IAM user: {IAM_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM user '{IAM_USERNAME}' already exists, continuing...")

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowS3Put",
                "Effect": "Allow",
                "Action": "s3:PutObject",
                "Resource": [
                    f"arn:aws:s3:::{S3_BUCKET_BETA}/*",
                    f"arn:aws:s3:::{S3_BUCKET_PROD}/*",
                ],
            },
            {
                "Sid": "AllowBedrock",
                "Effect": "Allow",
                "Action": "bedrock:InvokeModel",
                "Resource": MODEL_ARN,
            },
        ],
    }
    iam.put_user_policy(UserName=IAM_USERNAME, PolicyName=POLICY_NAME, PolicyDocument=json.dumps(policy))
    print(f"Attached policy: s3:PutObject (both buckets) + bedrock:InvokeModel (Claude 3 Sonnet)")


def create_access_key():
    for key in iam.list_access_keys(UserName=IAM_USERNAME)["AccessKeyMetadata"]:
        iam.delete_access_key(UserName=IAM_USERNAME, AccessKeyId=key["AccessKeyId"])
    key = iam.create_access_key(UserName=IAM_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up CAI_04/foundational...")
    print(f"  Beta bucket: {S3_BUCKET_BETA}")
    print(f"  Prod bucket: {S3_BUCKET_PROD}")
    print(f"  Region:      {AWS_REGION}\n")

    create_bucket(S3_BUCKET_BETA, "beta")
    create_bucket(S3_BUCKET_PROD, "prod")
    create_iam_user()
    access_key_id, secret = create_access_key()

    print(f"\nSuccess. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET_BETA        = {S3_BUCKET_BETA}")
    print(f"  S3_BUCKET_PROD        = {S3_BUCKET_PROD}")
    print(f"\nRun locally:")
    print(f"  S3_BUCKET={S3_BUCKET_BETA} ENV=beta AWS_REGION={AWS_REGION} \\")
    print(f"  /tmp/cai01-venv/bin/python CAI_04/foundational/process_prompt.py")
    print(f"\nStore the secret key securely — it will not be shown again.")
