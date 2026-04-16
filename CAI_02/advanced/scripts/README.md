# CAI_02 / Advanced — Setup Scripts

Provisions all AWS resources needed for the event-driven Rekognition pipeline.

## What It Creates

- DynamoDB tables: `beta_results`, `prod_results` (if not already created)
- IAM Lambda execution role with least-privilege permissions
- Lambda functions: `rekognition-beta-handler`, `rekognition-prod-handler`
- S3 event notifications wiring each prefix to its Lambda
- CI IAM user for GitHub Actions with `lambda:UpdateFunctionCode`, `s3:PutObject`, `dynamodb:Scan`

## Prerequisites

- AWS CLI configured (`aws configure`)
- S3 bucket already created
- Python venv active with boto3 installed

## Run

```bash
S3_BUCKET=your-bucket-name AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_02/advanced/scripts/setup_advanced.py
```

## Output

Prints all GitHub Actions secrets on completion, including `BETA_LAMBDA_ARN` and `PROD_LAMBDA_ARN` which are also needed by the complex tier.
