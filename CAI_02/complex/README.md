# Complex: Full IaC Rekognition Pipeline (CloudFormation)

All infrastructure — DynamoDB, Lambda, IAM roles — is defined in a single parameterized CloudFormation template. GitHub Actions deploys the stack and wires up S3 event notifications automatically.

```
GitHub Actions
  → cloudformation deploy (env=beta|prod)
  → lambda update-function-code
  → configure_s3_notifications.py
  → s3 cp images → rekognition-input/{env}/
       ↓ S3 trigger
   Lambda (rekognition-{env}-handler)
       ↓
   Rekognition detect_labels → DynamoDB ({env}_results)
```

---

## Step-by-Step Deployment

### Step 1: Create an S3 Bucket

Go to AWS Console → S3 → Create bucket. Any name, any region. Note the bucket name — you'll use it throughout.

---

### Step 2: Create an IAM User for GitHub Actions

Go to AWS Console → IAM → Users → Create user.

1. Name it something like `rekognition-cicd`
2. Attach an inline policy with these permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "cloudformation:*",
    "lambda:*",
    "s3:*",
    "rekognition:DetectLabels",
    "dynamodb:*",
    "iam:CreateRole",
    "iam:AttachRolePolicy",
    "iam:PassRole",
    "iam:GetRole",
    "iam:DeleteRole",
    "iam:DetachRolePolicy",
    "logs:*"
  ],
  "Resource": "*"
}
```

3. Go to **Security credentials** → **Create access key** → choose **Application running outside AWS**
4. Save the **Access Key ID** and **Secret Access Key**

---

### Step 3: Deploy the CloudFormation Stacks (First Time)

Run these commands locally to create the beta and prod stacks. Replace `your-bucket` with your actual bucket name.

**macOS / Linux**
```bash
# Deploy beta stack
aws cloudformation deploy \
  --template-file CAI_02/complex/cloudformation/template.yml \
  --stack-name rekognition-beta-stack \
  --parameter-overrides Env=beta S3BucketName=your-bucket \
  --capabilities CAPABILITY_NAMED_IAM

# Deploy prod stack
aws cloudformation deploy \
  --template-file CAI_02/complex/cloudformation/template.yml \
  --stack-name rekognition-prod-stack \
  --parameter-overrides Env=prod S3BucketName=your-bucket \
  --capabilities CAPABILITY_NAMED_IAM
```

**Windows (PowerShell)**
```powershell
# Deploy beta stack
aws cloudformation deploy `
  --template-file CAI_02/complex/cloudformation/template.yml `
  --stack-name rekognition-beta-stack `
  --parameter-overrides Env=beta S3BucketName=your-bucket `
  --capabilities CAPABILITY_NAMED_IAM

# Deploy prod stack
aws cloudformation deploy `
  --template-file CAI_02/complex/cloudformation/template.yml `
  --stack-name rekognition-prod-stack `
  --parameter-overrides Env=prod S3BucketName=your-bucket `
  --capabilities CAPABILITY_NAMED_IAM
```

---

### Step 4: Get the Lambda ARNs

After both stacks deploy, grab the Lambda ARNs from the stack outputs:

**macOS / Linux**
```bash
aws cloudformation describe-stacks --stack-name rekognition-beta-stack \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" --output text

aws cloudformation describe-stacks --stack-name rekognition-prod-stack \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" --output text
```

**Windows (PowerShell)**
```powershell
aws cloudformation describe-stacks --stack-name rekognition-beta-stack `
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" --output text

aws cloudformation describe-stacks --stack-name rekognition-prod-stack `
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" --output text
```

Save both ARN values — you'll add them as GitHub secrets in the next step.

---

### Step 5: Add GitHub Secrets

Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add all eight secrets:

| Secret Name             | Value                                        |
|-------------------------|----------------------------------------------|
| `AWS_ACCESS_KEY_ID`     | From the IAM user you created                |
| `AWS_SECRET_ACCESS_KEY` | From the IAM user you created                |
| `AWS_REGION`            | e.g. `us-east-1`                             |
| `S3_BUCKET`             | Your S3 bucket name                          |
| `DYNAMODB_TABLE_BETA`   | `beta_results`                               |
| `DYNAMODB_TABLE_PROD`   | `prod_results`                               |
| `BETA_LAMBDA_ARN`       | ARN from `rekognition-beta-stack` output     |
| `PROD_LAMBDA_ARN`       | ARN from `rekognition-prod-stack` output     |

---

### Step 6: Add an Image and Open a Pull Request

Add a `.jpg` or `.png` to `CAI_02/foundational/images/`, then push to a new branch:

```bash
git checkout -b feature/test-rekognition
git add project/foundational/images/
git commit -m "add image for rekognition analysis"
git push -u origin feature/test-rekognition
```

Open a pull request from `feature/test-rekognition` → `main` on GitHub. The **beta workflow** triggers automatically — watch it under the **Actions** tab.

---

### Step 7: Verify Beta Results

```bash
aws dynamodb scan --table-name beta_results
```

---

### Step 8: Merge to Trigger Prod

Merge the pull request. The **prod workflow** triggers automatically.

```bash
aws dynamodb scan --table-name prod_results
```

---

## What CloudFormation Provisions

One stack per environment (`rekognition-beta-stack`, `rekognition-prod-stack`), each containing:

| Resource              | Name                                                        |
|-----------------------|-------------------------------------------------------------|
| DynamoDB Table        | `beta_results` / `prod_results`                             |
| Lambda Function       | `rekognition-beta-handler` / `rekognition-prod-handler`     |
| IAM Execution Role    | `rekognition-beta-lambda-role` / `rekognition-prod-lambda-role` |

S3 bucket and event notifications are configured separately (S3 bucket notifications can't be managed by two stacks simultaneously).

---

## IAM Permissions — Least Privilege

The Lambda execution role is scoped tightly:

- `s3:GetObject` — only on `rekognition-input/{env}/*`
- `rekognition:DetectLabels` — all resources (required by Rekognition)
- `dynamodb:PutItem` — only on the environment's own table
- CloudWatch Logs — only on the function's own log group

---

## GitHub Secrets Reference

| Secret Name             | Description                                      |
|-------------------------|--------------------------------------------------|
| `AWS_ACCESS_KEY_ID`     | IAM access key                                   |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key                                   |
| `AWS_REGION`            | e.g. `us-east-1`                                 |
| `S3_BUCKET`             | Existing S3 bucket name                          |
| `DYNAMODB_TABLE_BETA`   | `beta_results`                                   |
| `DYNAMODB_TABLE_PROD`   | `prod_results`                                   |
| `BETA_LAMBDA_ARN`       | ARN of `rekognition-beta-handler` (after first deploy) |
| `PROD_LAMBDA_ARN`       | ARN of `rekognition-prod-handler` (after first deploy) |

> `BETA_LAMBDA_ARN` and `PROD_LAMBDA_ARN` are needed by `configure_s3_notifications.py`
> to set both prefixes in one call. After the first deploy, grab the ARNs from the
> CloudFormation stack outputs and add them as secrets.
