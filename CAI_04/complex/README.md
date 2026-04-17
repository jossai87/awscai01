# Complex: Full IaC Prompt Pipeline (CloudFormation)

All infrastructure — Lambda, IAM roles, S3 event triggers — defined in a single parameterized CloudFormation template. GitHub Actions deploys the stack, pushes code, and uploads prompts.

```
GitHub Actions
  → cloudformation deploy (Env=beta|prod)
  → lambda update-function-code
  → s3 cp prompt_templates/ + prompt_inputs/ (with env metadata)
       ↓ S3 trigger
   Lambda (prompt-pipeline-{env}-handler)
       ↓
   Load template → Render → Bedrock (Claude 3 Sonnet) → S3 output
       ↓
   {env}/outputs/{slug}.html or .md
```

---

## Setup

**macOS / Linux**
```bash
S3_BUCKET_BETA=your-beta-bucket S3_BUCKET_PROD=your-prod-bucket AWS_REGION=us-east-1 \
  python3 CAI_04/complex/scripts/setup_complex.py
```

**Windows (PowerShell)**
```powershell
$env:S3_BUCKET_BETA = "your-beta-bucket"
$env:S3_BUCKET_PROD = "your-prod-bucket"
$env:AWS_REGION = "us-east-1"
python CAI_04/complex/scripts/setup_complex.py
```

---

## GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | CI IAM access key |
| `AWS_SECRET_ACCESS_KEY` | CI IAM secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET_BETA` | Beta bucket |
| `S3_BUCKET_PROD` | Prod bucket |

---

## Verify Outputs

**macOS / Linux**
```bash
aws s3 ls s3://your-beta-bucket/beta/outputs/
aws s3 ls s3://your-prod-bucket/prod/outputs/
```

**Windows (PowerShell)**
```powershell
aws s3 ls s3://your-beta-bucket/beta/outputs/
aws s3 ls s3://your-prod-bucket/prod/outputs/
```
