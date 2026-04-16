"""
setup_foundational.py
---------------------
Provisions all AWS resources required for CAI_03/foundational:

  1. IAM user with least-privilege permissions:
       - s3:PutObject, s3:GetObject on your bucket
       - transcribe:StartTranscriptionJob, transcribe:GetTranscriptionJob
       - translate:TranslateText
       - polly:SynthesizeSpeech

On success, prints all GitHub Actions secrets needed.

Usage:
  python CAI_03/foundational/scripts/setup_foundational.py

Required env vars:
  S3_BUCKET   — S3 bucket name (must already exist)
  AWS_REGION  — defaults to us-east-1
"""

import boto3
import json
import os
import sys

S3_BUCKET    = os.environ.get("S3_BUCKET")
AWS_REGION   = os.environ.get("AWS_REGION", "us-east-1")
IAM_USERNAME = "multilingual-foundational-user"
POLICY_NAME  = "MultilingualFoundationalPolicy"

if not S3_BUCKET:
    print("Error: S3_BUCKET environment variable is required.")
    sys.exit(1)

iam = boto3.client("iam", region_name=AWS_REGION)

policy = {
    "Version": "2012-10-17",
    "Statement": [
        {"Sid": "AllowS3",         "Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"},
        {"Sid": "AllowTranscribe", "Effect": "Allow", "Action": ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"], "Resource": "*"},
        {"Sid": "AllowTranslate",  "Effect": "Allow", "Action": "translate:TranslateText", "Resource": "*"},
        {"Sid": "AllowPolly",      "Effect": "Allow", "Action": "polly:SynthesizeSpeech",  "Resource": "*"},
    ],
}


def create_user():
    try:
        iam.create_user(UserName=IAM_USERNAME)
        print(f"Created IAM user: {IAM_USERNAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM user '{IAM_USERNAME}' already exists, continuing...")
    iam.put_user_policy(UserName=IAM_USERNAME, PolicyName=POLICY_NAME, PolicyDocument=json.dumps(policy))
    print(f"Attached policy: s3, transcribe, translate, polly")


def create_access_key():
    for key in iam.list_access_keys(UserName=IAM_USERNAME)["AccessKeyMetadata"]:
        iam.delete_access_key(UserName=IAM_USERNAME, AccessKeyId=key["AccessKeyId"])
    key = iam.create_access_key(UserName=IAM_USERNAME)["AccessKey"]
    return key["AccessKeyId"], key["SecretAccessKey"]


if __name__ == "__main__":
    print(f"\nSetting up CAI_03/foundational...")
    print(f"  Bucket: {S3_BUCKET} | Region: {AWS_REGION}\n")
    create_user()
    access_key_id, secret = create_access_key()
    print(f"\nSuccess. Add these as GitHub Actions secrets:\n")
    print(f"  AWS_ACCESS_KEY_ID     = {access_key_id}")
    print(f"  AWS_SECRET_ACCESS_KEY = {secret}")
    print(f"  AWS_REGION            = {AWS_REGION}")
    print(f"  S3_BUCKET             = {S3_BUCKET}")
    print(f"\nRun locally:")
    print(f"  S3_BUCKET={S3_BUCKET} ENV=beta TARGET_LANG=es AWS_REGION={AWS_REGION} \\")
    print(f"  python3 CAI_03/foundational/process_audio.py")
    print(f"\nStore the secret key securely — it will not be shown again.")
