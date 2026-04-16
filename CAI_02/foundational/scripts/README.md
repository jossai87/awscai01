# CAI_02 / Foundational — Setup Scripts

Provisions all AWS resources needed before running the foundational Rekognition pipeline.

## What It Creates

- DynamoDB tables: `beta_results` and `prod_results`
- IAM user `rekognition-foundational-user` with least-privilege permissions:
  - `s3:PutObject` on your bucket
  - `rekognition:DetectLabels`
  - `dynamodb:PutItem` on both tables

## Prerequisites

- AWS CLI configured (`aws configure`)
- S3 bucket already created
- Python venv active with boto3 installed

## Run

```bash
S3_BUCKET=your-bucket-name AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_02/foundational/scripts/setup_foundational.py
```

## Output

Prints all six GitHub Actions secrets on completion.

## Run the Pipeline Locally

```bash
S3_BUCKET=your-bucket \
DYNAMODB_TABLE=beta_results \
BRANCH=my-branch \
AWS_REGION=us-east-1 \
/tmp/cai01-venv/bin/python CAI_02/foundational/analyze_image.py
```
