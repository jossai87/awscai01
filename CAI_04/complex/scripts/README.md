# CAI_04 / Complex — Setup Scripts

Deploys the full prompt pipeline infrastructure using CloudFormation.

## What It Creates

- `prompt-pipeline-beta-stack` and `prompt-pipeline-prod-stack` via CloudFormation
- Lambda code deployed to both functions
- S3 event notifications: `prompt_inputs/*.json` → Lambda (per bucket)
- Prompt templates uploaded to both buckets
- CI IAM user for GitHub Actions

## Run

```bash
S3_BUCKET_BETA=your-beta-bucket S3_BUCKET_PROD=your-prod-bucket AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_04/complex/scripts/setup_complex.py
```

## Re-running

Safe to run multiple times — CloudFormation skips unchanged stacks.
