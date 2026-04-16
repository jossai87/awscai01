# CAI_02 / Complex — Setup Scripts

Deploys the full Rekognition pipeline infrastructure using CloudFormation.

## What It Does

1. Deploys `rekognition-beta-stack` and `rekognition-prod-stack` from `cloudformation/template.yml`
2. Pushes `handler.py` code to both Lambda functions
3. Configures S3 event notifications for `rekognition-input/beta/` and `rekognition-input/prod/`
4. Creates a CI IAM user for GitHub Actions

Each CloudFormation stack provisions: DynamoDB table, Lambda function, IAM execution role.

## Prerequisites

- AWS CLI configured (`aws configure`)
- S3 bucket already created
- Python venv active with boto3 installed
- IAM user running the script needs: `cloudformation:*`, `lambda:*`, `iam:*`, `s3:PutBucketNotification`

## Run

```bash
S3_BUCKET=your-bucket-name AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_02/complex/scripts/setup_complex.py
```

## Output

Prints all GitHub Actions secrets on completion including `BETA_LAMBDA_ARN` and `PROD_LAMBDA_ARN`.

## Re-running

Safe to run multiple times — CloudFormation skips unchanged stacks.
