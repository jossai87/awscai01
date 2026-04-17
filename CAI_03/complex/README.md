# Complex: Full IaC Multilingual Audio Pipeline (CloudFormation)

All infrastructure — Lambda, IAM roles, S3 event trigger — defined in a single parameterized CloudFormation template. GitHub Actions deploys the stack and uploads audio automatically.

```
GitHub Actions
  → cloudformation deploy (Env=beta|prod)
  → lambda update-function-code
  → s3 cp audio_inputs/*.mp3 (with env metadata)
       ↓ S3 trigger
   Lambda (multilingual-{env}-handler)
       ↓
   Transcribe → Translate → Polly
       ↓
   S3: {env}/transcripts/, translations/, audio_outputs/
```

---

## What CloudFormation Provisions

One stack per environment (`multilingual-beta-stack`, `multilingual-prod-stack`):

| Resource | Name |
|----------|------|
| Lambda Function | `multilingual-beta-handler` / `multilingual-prod-handler` |
| IAM Execution Role | `multilingual-beta-lambda-role` / `multilingual-prod-lambda-role` |

---

## Setup

**macOS / Linux**
```bash
S3_BUCKET=your-bucket AWS_REGION=us-east-1 TARGET_LANG=es \
  python3 CAI_03/complex/scripts/setup_complex.py
```

**Windows (PowerShell)**
```powershell
$env:S3_BUCKET = "your-bucket"
$env:AWS_REGION = "us-east-1"
$env:TARGET_LANG = "es"
python CAI_03/complex/scripts/setup_complex.py
```

---

## GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | CI IAM access key |
| `AWS_SECRET_ACCESS_KEY` | CI IAM secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET` | Your bucket name |

---

## Verify Outputs

**macOS / Linux**
```bash
aws s3 ls s3://your-bucket/beta/transcripts/
aws s3 ls s3://your-bucket/beta/translations/
aws s3 ls s3://your-bucket/beta/audio_outputs/
```

**Windows (PowerShell)**
```powershell
aws s3 ls s3://your-bucket/beta/transcripts/
aws s3 ls s3://your-bucket/beta/translations/
aws s3 ls s3://your-bucket/beta/audio_outputs/
```
