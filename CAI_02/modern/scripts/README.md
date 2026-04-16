# CAI_02 / Modern — Setup Scripts

Provisions all AWS resources needed for the Nova 2 Lite image analysis pipeline.

## What It Creates

- DynamoDB tables: `beta_results`, `prod_results` (if not already created)
- IAM user with permissions for `bedrock:InvokeModel`, `s3:PutObject`, `s3:GetObject`, `dynamodb:PutItem`
- Checks Nova 2 Lite model access status in Bedrock

## Prerequisites

- AWS CLI configured (`aws configure`)
- S3 bucket already created
- Python venv active with boto3 installed
- Region must be Nova-supported: `us-east-1`, `us-west-2`, `eu-west-1`, `ap-northeast-1`
- Nova 2 Lite enabled in Bedrock Console → Model access (go enable it before running)

## Run

```bash
S3_BUCKET=your-bucket-name AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_02/modern/scripts/setup_modern.py
```

## Output

Prints all GitHub Actions secrets and a local run command on completion.
