# CAI_03 / Complex — Setup Scripts

Deploys the full multilingual audio pipeline infrastructure using CloudFormation.

## What It Creates

- `multilingual-beta-stack` and `multilingual-prod-stack` via CloudFormation
- Lambda code deployed to both functions after stack creation
- S3 event notifications: `audio_inputs/*.mp3` → Lambda
- CI IAM user for GitHub Actions

## Run

```bash
S3_BUCKET=your-bucket AWS_REGION=us-east-1 TARGET_LANG=es \
  /tmp/cai01-venv/bin/python CAI_03/complex/scripts/setup_complex.py
```

## Re-running

Safe to run multiple times — CloudFormation skips unchanged stacks.
