# Pixel Learning Co. — AWS AI Pipeline Projects

This repository contains a series of AWS AI integration projects built for Pixel Learning Co. Each project (`CAI_01`, `CAI_02`, etc.) is self-contained and structured across three tiers: **foundational**, **advanced**, and **complex**.

---

## Prerequisites

Before running any project, make sure you have the following set up:

### 1. AWS CLI

Install the AWS CLI if you haven't already: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html

### 2. Configure AWS Credentials

Run the following and enter your credentials when prompted:

```bash
aws configure
```

Or set them explicitly:

```bash
aws configure set aws_access_key_id YOUR_ACCESS_KEY_ID
aws configure set aws_secret_access_key YOUR_SECRET_ACCESS_KEY
aws configure set region us-east-1
```

You'll need an IAM user or role with permissions appropriate to the project you're running. Each project's README lists the exact permissions required.

### 3. Python 3.11+

All scripts use Python 3.11. On macOS, the system Python environment is externally managed and blocks direct `pip install`. Use a virtual environment instead:

```bash
python3 -m venv ~/.venvs/awsai
source ~/.venvs/awsai/bin/activate
pip install boto3
```

Once activated, run scripts with the required env vars inline:

```bash
S3_BUCKET_NAME=your-bucket AWS_REGION=us-east-1 OUTPUT_KEY=polly-audio/output.mp3 python3 synthesize.py
```

The venv stays active for your terminal session. Run `deactivate` to exit it.

---

## Dependencies by Project

### CAI_01 / foundational
```bash
pip install boto3
```
Also needs: AWS credentials with `polly:SynthesizeSpeech` and `s3:PutObject`

### CAI_01 / advanced & complex (Lambda)
Lambda functions run on AWS — `boto3` is pre-installed in the Lambda runtime. No local install needed unless testing locally.

### CAI_01 / modern
```bash
pip install boto3 aws-sdk-bedrock-runtime smithy-aws-core
```
Also needs:
- `ffmpeg` installed on your machine (`brew install ffmpeg`)
- A `sample_input.wav` audio file in `CAI_01/modern/`
- Nova 2 Sonic enabled in Bedrock Console → Model access
- IAM permission: `bedrock:InvokeModelWithBidirectionalStream`

Run command:
```bash
S3_BUCKET_NAME=your-bucket \
AWS_REGION=us-east-1 \
OUTPUT_KEY=nova-audio/output.mp3 \
INPUT_AUDIO_FILE=CAI_01/modern/sample_input.wav \
python3 CAI_01/modern/synthesize.py
```

### CAI_02 / foundational
```bash
pip install boto3
```
Also needs: IAM permissions for `rekognition:DetectLabels`, `s3:PutObject`, `dynamodb:PutItem`

Run command:
```bash
S3_BUCKET=your-bucket \
DYNAMODB_TABLE=beta_results \
BRANCH=my-branch \
AWS_REGION=us-east-1 \
python3 CAI_02/foundational/analyze_image.py
```

### CAI_02 / advanced & complex (Lambda)
Lambda functions run on AWS — `boto3` is pre-installed. No local install needed.

### CAI_02 / modern
```bash
pip install boto3
```
Also needs:
- Nova 2 Lite enabled in Bedrock Console → Model access
- IAM permissions: `bedrock:InvokeModel`, `s3:PutObject`, `s3:GetObject`, `dynamodb:PutItem`

Run command:
```bash
S3_BUCKET=your-bucket \
DYNAMODB_TABLE=beta_results \
BRANCH=my-branch \
AWS_REGION=us-east-1 \
python3 CAI_02/modern/analyze_image.py
```

---

## Projects

### CAI_01 — Amazon Polly Text-to-Speech Pipeline

Converts text course content into audio using Amazon Polly and uploads it to S3.

| Tier | Description |
|------|-------------|
| `foundational` | Python script + GitHub Actions CI/CD. Reads `speech.txt`, synthesizes MP3 via Polly, uploads to S3. |
| `advanced` | Lambda + API Gateway. GitHub Actions deploys and invokes environment-specific Lambda functions. |
| `complex` | CloudFormation templates provision the full stack (Lambda, API Gateway, IAM). Terraform backend config included. |
| `sagemaker` | Jupyter notebooks for running each tier interactively inside Amazon SageMaker. |

→ See [`CAI_01/foundational/README.md`](CAI_01/foundational/README.md) to get started.

---

### CAI_02 — Amazon Rekognition Image Labeling Pipeline

Automatically classifies images using Amazon Rekognition and logs results to branch-specific DynamoDB tables.

| Tier | Description |
|------|-------------|
| `foundational` | Python script + GitHub Actions. Uploads images to S3, calls `detect_labels`, writes results to DynamoDB. |
| `advanced` | Event-driven via Lambda + S3 triggers. GitHub Actions only uploads images; Rekognition runs inside Lambda. |
| `complex` | Full CloudFormation IaC. Single parameterized template deploys DynamoDB, Lambda, and IAM per environment. |

→ See [`CAI_02/foundational/README.md`](CAI_02/foundational/README.md) to get started.

---

### CAI_03 — Multilingual Audio Pipeline

Transcribes English .mp3 files, translates the text, and synthesizes speech in the target language using Amazon Transcribe, Translate, and Polly.

| Tier | Description |
|------|-------------|
| `foundational` | Python script + GitHub Actions. Transcribe → Translate → Polly → structured S3 outputs. |
| `advanced` | Event-driven Lambda triggered by S3 uploads. GitHub Actions only uploads the .mp3 with env metadata. |
| `complex` | Full CloudFormation IaC. Parameterized stacks for beta/prod with least-privilege IAM roles. |

→ See [`CAI_03/foundational/README.md`](CAI_03/foundational/README.md) to get started.

---

### CAI_04 — Bedrock Prompt Deployment Pipeline

Reads structured prompt configs, renders templates, sends them to Amazon Bedrock (Claude 3 Sonnet), and publishes generated content as HTML/MD to S3 static website buckets.

| Tier | Description |
|------|-------------|
| `foundational` | Python script + GitHub Actions. Template rendering → Bedrock → S3 static site. |
| `advanced` | Event-driven Lambda triggered by S3 uploads of prompt configs. GitHub Actions only uploads. |
| `complex` | Full CloudFormation IaC. Parameterized stacks for beta/prod with least-privilege IAM roles. |

→ See [`CAI_04/foundational/README.md`](CAI_04/foundational/README.md) to get started.

---

## Repository Structure

```
.
├── CAI_01/
│   ├── foundational/       # Polly script + GitHub Actions workflows
│   ├── advanced/           # Lambda + API Gateway
│   ├── complex/            # CloudFormation + Terraform
│   └── sagemaker/          # Jupyter notebooks
├── CAI_02/
│   ├── foundational/       # Rekognition script + GitHub Actions workflows
│   ├── advanced/           # Lambda + S3 event triggers
│   └── complex/            # CloudFormation IaC
├── CAI_03/
└── CAI_04/
```

---

## GitHub Actions Setup

Each tier has its own `.github/workflows/` folder with two workflows:

- `on_pull_request.yml` — runs on PRs targeting `main`, writes to beta resources
- `on_merge.yml` — runs on push to `main`, writes to prod resources

Add the required secrets under **Settings → Secrets and variables → Actions** in your GitHub repo. Each project's README lists exactly which secrets are needed.
