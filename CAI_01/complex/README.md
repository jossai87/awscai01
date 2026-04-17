# Complex: CloudFormation Polly Pipeline

Full infrastructure-as-code deployment of the Polly TTS pipeline using CloudFormation. Two environment-specific stacks provision everything — IAM roles, Lambda functions, and API Gateway — with strict least-privilege policies.

```
GitHub PR    →  polly-beta-stack  →  PollyTextToSpeech_Beta  →  POST /beta/synthesize  →  S3: polly-audio/beta/
GitHub Merge →  polly-prod-stack  →  PollyTextToSpeech_Prod  →  POST /prod/synthesize  →  S3: polly-audio/prod/
```

---

## What CloudFormation Provisions

Each stack (`template-beta.yml` / `template-prod.yml`) creates:

| Resource    | Beta                      | Prod                      |
|-------------|---------------------------|---------------------------|
| IAM Role    | `PollyBetaExecutionRole`  | `PollyProdExecutionRole`  |
| Lambda      | `PollyTextToSpeech_Beta`  | `PollyTextToSpeech_Prod`  |
| API Gateway | `PollyBetaAPI`            | `PollyProdAPI`            |
| S3 path     | `polly-audio/beta/*`      | `polly-audio/prod/*`      |

The beta role includes an explicit `Deny` on `polly-audio/prod/*` to prevent cross-environment writes.

---

## Step 1 — Prerequisites

Confirm your AWS CLI is configured:

```bash
aws sts get-caller-identity
```

Set up your Python virtual environment and install boto3:

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

> Already done from a previous project? Just activate it:
> - macOS/Linux: `source /tmp/cai01-venv/bin/activate`
> - Windows: `C:\cai01-venv\Scripts\Activate.ps1`

Your IAM user needs these permissions:
- `cloudformation:*`
- `lambda:*`
- `apigateway:*`
- `iam:*`
- `s3:PutObject`

---

## Step 2 — S3 Bucket

Your bucket is already created: **`cai-01-jossai-1`** in `us-east-1`. No action needed here.

---

## Step 3 — Deploy Both CloudFormation Stacks

**macOS / Linux**
```bash
source /tmp/cai01-venv/bin/activate

export S3_BUCKET_NAME=cai-01-jossai-1
export AWS_REGION=us-east-1

python3 "CAI_01/complex/scripts/setup_complex.py"
```

**Windows (PowerShell)**
```powershell
C:\cai01-venv\Scripts\Activate.ps1

$env:S3_BUCKET_NAME = "cai-01-jossai-1"
$env:AWS_REGION = "us-east-1"

python "CAI_01/complex/scripts/setup_complex.py"
```

The script will print output like this when complete:

```
Success. Add these as GitHub Actions secrets:

  BETA_API_ENDPOINT = https://abc123.execute-api.us-east-1.amazonaws.com/beta
  PROD_API_ENDPOINT = https://xyz789.execute-api.us-east-1.amazonaws.com/prod

Test the endpoints:
  curl -X POST https://abc123.execute-api.us-east-1.amazonaws.com/beta/synthesize \
    -H 'Content-Type: application/json' \
    -d '{"text": "Hello from beta"}'
```

> **Note:** The script is safe to re-run. CloudFormation will update existing stacks or skip if nothing changed.

---

## Step 4 — Verify the Stacks Deployed Successfully

```bash
# Check both stacks are in CREATE_COMPLETE or UPDATE_COMPLETE
aws cloudformation describe-stacks \
  --query 'Stacks[?StackName==`polly-beta-stack` || StackName==`polly-prod-stack`].[StackName,StackStatus]' \
  --output table

# View all resources created by the beta stack
aws cloudformation describe-stack-resources \
  --stack-name polly-beta-stack \
  --query 'StackResources[].[ResourceType,PhysicalResourceId,ResourceStatus]' \
  --output table
```

---

## Step 5 — Test the Endpoints Manually

Before adding secrets to GitHub, confirm both endpoints work:

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

## Step 6 — Add GitHub Secrets

Go to **https://github.com/jossai87/awsai01/settings/secrets/actions** and add all five:

| Secret                  | Value                                               |
|-------------------------|-----------------------------------------------------|
| `AWS_ACCESS_KEY_ID`     | IAM credentials                                    |
| `AWS_SECRET_ACCESS_KEY` | IAM credentials                                    |
| `AWS_REGION`            | e.g. `us-east-1`                                   |
| `BETA_API_ENDPOINT`     | Base URL printed by setup script (no `/synthesize`) |
| `PROD_API_ENDPOINT`     | Base URL printed by setup script (no `/synthesize`) |

---

## Step 7 — Trigger the Workflows

### Trigger beta (via Pull Request)

```bash
git checkout -b test/complex-beta
git commit --allow-empty -m "test: trigger complex beta deployment"
git push origin test/complex-beta
```

Then open a Pull Request on GitHub targeting `main`. The workflow deploys updated Lambda code to `PollyTextToSpeech_Beta` and calls the beta endpoint.

### Trigger prod (via Merge)

Merge the PR into `main`. The workflow deploys updated Lambda code to `PollyTextToSpeech_Prod` and calls the prod endpoint.

---

## Step 8 — Verify the Uploaded Files

```bash
# List beta audio files
aws s3 ls s3://cai-01-jossai-1/polly-audio/beta/

# List prod audio files
aws s3 ls s3://cai-01-jossai-1/polly-audio/prod/

# Download a file to listen locally
aws s3 cp s3://cai-01-jossai-1/polly-audio/beta/ ./beta-audio/ --recursive
```

---

## Tear Down (Optional)

To delete all provisioned resources and avoid ongoing costs:

```bash
# Delete both stacks (removes IAM roles, Lambda functions, API Gateways)
aws cloudformation delete-stack --stack-name polly-beta-stack
aws cloudformation delete-stack --stack-name polly-prod-stack

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name polly-beta-stack
aws cloudformation wait stack-delete-complete --stack-name polly-prod-stack

echo "Both stacks deleted."
```

> **Note:** This does NOT delete your S3 bucket or the audio files inside it.

---

## Troubleshooting

**Stack creation fails** — Check the CloudFormation events for the error:

```bash
aws cloudformation describe-stack-events \
  --stack-name polly-beta-stack \
  --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
  --output table
```

**Lambda not updating after stack deploy** — The setup script pushes the real handler code after CloudFormation finishes. If it failed, run the script again — it is idempotent.

**curl returns 403 or 500** — Check Lambda logs in CloudWatch:

```bash
aws logs tail /aws/lambda/PollyTextToSpeech_Beta --follow
aws logs tail /aws/lambda/PollyTextToSpeech_Prod --follow
```

**Check workflow logs** — Go to your GitHub repo → **Actions** tab → click the workflow run to see detailed logs.

---

## Structure

```
complex/
├── cloudformation/
│   ├── template-beta.yml   # Beta stack — IAM + Lambda + API Gateway
│   └── template-prod.yml   # Prod stack — IAM + Lambda + API Gateway
├── lambda/
│   └── handler.py          # Deployed to both Lambda functions by setup script
├── scripts/
│   └── setup_complex.py    # Deploys stacks + pushes handler code
├── terraform/
│   └── backend.tf          # S3 backend config (alternative IaC option)
└── README.md
```
