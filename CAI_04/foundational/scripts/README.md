# CAI_04 / Foundational — Setup Scripts

Provisions S3 buckets with static website hosting and an IAM user for the prompt pipeline.

## What It Creates

- S3 bucket for beta with static website hosting enabled
- S3 bucket for prod with static website hosting enabled
- IAM user with `s3:PutObject` on both buckets and `bedrock:InvokeModel` on Claude 3 Sonnet

## Prerequisites

- AWS CLI configured (`aws configure`)
- Claude 3 Sonnet enabled in Bedrock Console → Model access
- Python venv active with boto3 installed

## Run

```bash
S3_BUCKET_BETA=your-beta-bucket S3_BUCKET_PROD=your-prod-bucket AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_04/foundational/scripts/setup_foundational.py
```

## Run the Pipeline Locally

```bash
S3_BUCKET=your-beta-bucket ENV=beta AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_04/foundational/process_prompt.py
```
