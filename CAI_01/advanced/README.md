# Advanced: Lambda + API Gateway Polly Pipeline

GitHub Actions deploys environment-specific Lambda functions and invokes them via API Gateway POST endpoints.

```
GitHub PR    →  Deploy PollyTextToSpeech_Beta  →  POST /beta/synthesize  →  S3: polly-audio/beta/{timestamp}.mp3
GitHub Merge →  Deploy PollyTextToSpeech_Prod  →  POST /prod/synthesize  →  S3: polly-audio/prod/{timestamp}.mp3
```

---

## How It Works

1. `setup_advanced.py` provisions all AWS infrastructure (IAM role, two Lambda functions, two API Gateways)
2. GitHub Actions deploys updated Lambda code on every PR (beta) and every merge (prod)
3. After deploying, the workflow calls the API Gateway endpoint with a POST request to trigger synthesis
4. The Lambda calls Polly, generates a timestamped MP3, and uploads it to S3

---

## Step 1 — S3 Bucket

Your bucket is already created: **`cai-01-jossai-1`** in `us-east-1`. No action needed here.

---

## Step 2 — Set Up Your Python Environment

If you haven't already, create the virtual environment and install boto3:

**macOS / Linux**
```bash
python3 -m venv /tmp/cai01-venv
source /tmp/cai01-venv/bin/activate
pip install boto3
```

**Windows (PowerShell)**
```powershell
python -m venv C:\cai01-venv
C:\cai01-venv\Scripts\Activate.ps1
pip install boto3
```

> Already done from the foundational project? Just activate it:
> - macOS/Linux: `source /tmp/cai01-venv/bin/activate`
> - Windows: `C:\cai01-venv\Scripts\Activate.ps1`

---

## Step 3 — Run the Infrastructure Setup Script

This creates the IAM role, both Lambda functions, and both API Gateways in one shot.

**macOS / Linux**
```bash
source /tmp/cai01-venv/bin/activate

export S3_BUCKET_NAME=cai-01-jossai-1
export AWS_REGION=us-east-1

python3 "CAI_01/advanced/scripts/setup_advanced.py"
```

**Windows (PowerShell)**
```powershell
C:\cai01-venv\Scripts\Activate.ps1

$env:S3_BUCKET_NAME = "cai-01-jossai-1"
$env:AWS_REGION = "us-east-1"

python "CAI_01/advanced/scripts/setup_advanced.py"
```

The script will print output like this when complete:

```
Done! Add these as GitHub Actions secrets:

  BETA_API_ENDPOINT = https://abc123.execute-api.us-east-1.amazonaws.com/beta
  PROD_API_ENDPOINT = https://xyz789.execute-api.us-east-1.amazonaws.com/prod

Test the endpoints:
  curl -X POST https://abc123.execute-api.us-east-1.amazonaws.com/beta/synthesize \
    -H 'Content-Type: application/json' \
    -d '{"text": "Hello from beta"}'
```

---

## Step 4 — Test the Endpoints Manually

Before adding secrets to GitHub, confirm the endpoints work:

```bash
# Test beta endpoint
curl -X POST https://<beta-id>.execute-api.us-east-1.amazonaws.com/beta/synthesize \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello from beta"}'

# Test prod endpoint
curl -X POST https://<prod-id>.execute-api.us-east-1.amazonaws.com/prod/synthesize \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello from prod"}'
```

A successful response looks like:

```json
{"message": "Audio synthesized", "s3_key": "polly-audio/beta/20260101T120000Z.mp3"}
```

---

## Step 5 — Add GitHub Secrets

Go to **https://github.com/jossai87/awsai01/settings/secrets/actions** and add all five:

| Secret                  | Value                                               |
|-------------------------|-----------------------------------------------------|
| `AWS_ACCESS_KEY_ID`     | IAM credentials (same user as foundational)         |
| `AWS_SECRET_ACCESS_KEY` | IAM credentials                                    |
| `AWS_REGION`            | e.g. `us-east-1`                                   |
| `BETA_API_ENDPOINT`     | Base URL printed by setup script (no `/synthesize`) |
| `PROD_API_ENDPOINT`     | Base URL printed by setup script (no `/synthesize`) |

> **Note:** `BETA_API_ENDPOINT` and `PROD_API_ENDPOINT` are the base URLs only — the workflow appends `/synthesize` automatically.

---

## Step 6 — Trigger the Workflows

### Trigger beta (via Pull Request)

```bash
git checkout -b test/advanced-beta
git commit --allow-empty -m "test: trigger advanced beta deployment"
git push origin test/advanced-beta
```

Then open a Pull Request on GitHub targeting `main`. The `on_pull_request.yml` workflow will:
1. Package `lambda/handler.py` into a ZIP
2. Deploy it to `PollyTextToSpeech_Beta`
3. Call the beta API Gateway endpoint to synthesize audio

### Trigger prod (via Merge)

Merge the PR into `main`. The `on_merge.yml` workflow will:
1. Package `lambda/handler.py` into a ZIP
2. Deploy it to `PollyTextToSpeech_Prod`
3. Call the prod API Gateway endpoint to synthesize audio

---

## Step 7 — Verify the Uploaded Files

```bash
# List beta audio files (timestamped)
aws s3 ls s3://cai-01-jossai-1/polly-audio/beta/

# List prod audio files
aws s3 ls s3://cai-01-jossai-1/polly-audio/prod/

# Download the most recent beta file
aws s3 cp s3://cai-01-jossai-1/polly-audio/beta/ ./beta-audio/ --recursive
```

---

## Re-running the Setup Script

Safe to re-run — updates existing resources instead of failing:

**macOS / Linux**
```bash
source /tmp/cai01-venv/bin/activate

export S3_BUCKET_NAME=cai-01-jossai-1
export AWS_REGION=us-east-1

python3 "CAI_01/advanced/scripts/setup_advanced.py"
```

**Windows (PowerShell)**
```powershell
C:\cai01-venv\Scripts\Activate.ps1

$env:S3_BUCKET_NAME = "cai-01-jossai-1"
$env:AWS_REGION = "us-east-1"

python "CAI_01/advanced/scripts/setup_advanced.py"
```

---

## Troubleshooting

**curl returns 403 or 500** — Check the Lambda function logs in CloudWatch:

```bash
aws logs tail /aws/lambda/PollyTextToSpeech_Beta --follow
aws logs tail /aws/lambda/PollyTextToSpeech_Prod --follow
```

**Lambda not updating** — The workflow waits for `function-updated`. If it times out, check the Lambda console for errors.

**Missing text in request body** — The endpoint expects JSON with a `text` field:

```bash
curl -X POST https://<your-endpoint>/synthesize \
  -H 'Content-Type: application/json' \
  -d '{"text": "Your text here"}'
```

**Check workflow logs** — Go to your GitHub repo → **Actions** tab → click the workflow run to see detailed logs.
