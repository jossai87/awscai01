# CAI_01 / Complex — Setup Scripts

Deploys the full Polly pipeline infrastructure using CloudFormation.

---

## What It Does

Runs `aws cloudformation deploy` for both environment stacks:

| Stack | Template | Lambda | Environment |
|-------|----------|--------|-------------|
| `polly-beta-stack` | `template-beta.yml` | `PollyTextToSpeech_Beta` | beta |
| `polly-prod-stack` | `template-prod.yml` | `PollyTextToSpeech_Prod` | prod |

Each stack provisions: IAM execution role, Lambda function, API Gateway REST API with `POST /synthesize`. After the stacks are up, the real `handler.py` code is deployed to both Lambda functions.

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- Your IAM user needs: `cloudformation:*`, `lambda:*`, `apigateway:*`, `iam:*`, `s3:PutObject`
- The venv with boto3 active (`source /tmp/cai01-venv/bin/activate`)

---

## Run

```bash
S3_BUCKET_NAME=jossai-levelup-caai01-2 AWS_REGION=us-east-1 \
  /tmp/cai01-venv/bin/python CAI_01/complex/scripts/setup_complex.py
```

---

## Output

On success the script prints the two API Gateway URLs to add as GitHub Actions secrets:

```
BETA_API_ENDPOINT = https://<id>.execute-api.us-east-1.amazonaws.com/beta
PROD_API_ENDPOINT = https://<id>.execute-api.us-east-1.amazonaws.com/prod
```

And curl commands to test each endpoint immediately.

---

## Re-running

Safe to run multiple times — CloudFormation will update existing stacks if there are changes, or skip if nothing has changed.
