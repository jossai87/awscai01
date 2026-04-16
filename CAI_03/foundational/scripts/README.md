# CAI_03 / Foundational — Setup Scripts

Provisions all AWS resources needed before running the foundational multilingual audio pipeline.

## What It Creates

- IAM user `multilingual-foundational-user` with least-privilege permissions:
  - `s3:PutObject`, `s3:GetObject` on your bucket
  - `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`
  - `translate:TranslateText`
  - `polly:SynthesizeSpeech`

## Prerequisites

- AWS CLI configured (`aws configure`)
- S3 bucket already created
- Python venv active with boto3 installed

## Run

```bash
S3_BUCKET=your-bucket-name AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_03/foundational/scripts/setup_foundational.py
```

## Run the Pipeline Locally

```bash
S3_BUCKET=your-bucket ENV=beta TARGET_LANG=es AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_03/foundational/process_audio.py
```
