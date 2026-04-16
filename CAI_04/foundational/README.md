# Foundational: Bedrock Prompt Deployment Pipeline

Reads structured prompt configs, renders templates with variables, sends them to Amazon Bedrock (Claude 3 Sonnet), and publishes the generated content as HTML/MD to S3 static website buckets.

```
prompts/*.json + prompt_templates/*.txt
  → Render template with variables
  → Bedrock (Claude 3 Sonnet, on-demand)
  → outputs/{slug}.html or .md
  → S3: {env}/outputs/{slug}.html
```

---

## Setup

```bash
S3_BUCKET_BETA=your-beta-bucket S3_BUCKET_PROD=your-prod-bucket AWS_REGION=us-east-1 \
  python3 CAI_04/foundational/scripts/setup_foundational.py
```

Creates S3 buckets with static website hosting and an IAM user with `bedrock:InvokeModel` + `s3:PutObject`.

---

## GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET_BETA` | Beta static site bucket |
| `S3_BUCKET_PROD` | Prod static site bucket |

---

## Adding Prompts

1. Create a template in `prompt_templates/` (e.g. `welcome_email.txt`)
2. Create a config in `prompts/` (e.g. `welcome_prompt.json`) referencing the template
3. Open a PR → beta workflow runs → output in `s3://beta-bucket/beta/outputs/`
4. Merge → prod workflow runs → output in `s3://prod-bucket/prod/outputs/`

### Config Format

```json
{
  "template": "welcome_email.txt",
  "output_filename": "welcome_jordan",
  "output_format": "html",
  "variables": {
    "student_name": "Jordan",
    "course_name": "Cloud Computing Fundamentals"
  }
}
```

---

## Verify Outputs

```bash
aws s3 ls s3://your-beta-bucket/beta/outputs/
aws s3 ls s3://your-prod-bucket/prod/outputs/
```

Or visit the static site URL printed by the setup script.

---

## Model

Uses `anthropic.claude-3-sonnet-20240229-v1:0` via on-demand (real-time) invocation only. No provisioned throughput.
