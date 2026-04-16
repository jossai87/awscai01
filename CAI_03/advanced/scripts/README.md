# CAI_03 / Advanced — Setup Scripts

Provisions all AWS resources for the event-driven multilingual audio pipeline.

## What It Creates

- Lambda execution role with transcribe, translate, polly, s3, logs permissions
- `multilingual-audio-handler` Lambda (timeout: 300s for Transcribe jobs)
- S3 event notification: `audio_inputs/*.mp3` → Lambda
- CI IAM user for GitHub Actions

## Run

```bash
S3_BUCKET=your-bucket AWS_REGION=us-east-1 TARGET_LANG=es \
  /tmp/cai01-venv/bin/python CAI_03/advanced/scripts/setup_advanced.py
```

## Output

Prints all GitHub Actions secrets and the Lambda ARN (needed by complex tier).
