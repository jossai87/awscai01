# Advanced: Event-Driven Prompt Pipeline (Lambda + S3 Trigger)

GitHub Actions uploads prompt configs to S3. An S3 event notification triggers a Lambda that renders the prompt, calls Bedrock, and publishes the output.

```
GitHub Actions
  → s3 cp prompt_inputs/*.json (with metadata env=beta|prod)
       ↓ S3 trigger
   Lambda (prompt-pipeline-handler)
       ↓
   Load template → Render prompt → Bedrock (Claude 3 Sonnet) → S3 output
       ↓
   {env}/outputs/{slug}.html or .md
```

---

## Setup

```bash
S3_BUCKET=your-bucket AWS_REGION=us-east-1 \
  python3 CAI_04/advanced/scripts/setup_advanced.py
```

---

## GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | CI IAM access key |
| `AWS_SECRET_ACCESS_KEY` | CI IAM secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET_BETA` | Your bucket name |

---

## How Environment Is Determined

Lambda reads `env` from S3 object metadata set by the upload workflow. Fallback: filename prefix (`beta-*.json` → beta, else prod).
