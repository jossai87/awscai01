# CAI_04 / Advanced — Setup Scripts

Provisions all AWS resources for the event-driven prompt pipeline.

## What It Creates

- Lambda execution role with bedrock:InvokeModel, s3 read/write, logs
- `prompt-pipeline-handler` Lambda function
- S3 event notification: `prompt_inputs/*.json` → Lambda
- Uploads prompt templates to S3 so Lambda can read them
- CI IAM user for GitHub Actions

## Run

```bash
S3_BUCKET=your-bucket AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_04/advanced/scripts/setup_advanced.py
```
