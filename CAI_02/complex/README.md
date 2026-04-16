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

## What CloudFormation Provisions

One stack per environment (`rekognition-beta-stack`, `rekognition-prod-stack`), each containing:

| Resource              | Name                              |
|-----------------------|-----------------------------------|
| DynamoDB Table        | `beta_results` / `prod_results`   |
| Lambda Function       | `rekognition-beta-handler` / `rekognition-prod-handler` |
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

## GitHub Secrets Required

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

---

## Deploying Manually (first time)

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

# Get Lambda ARNs and save as GitHub secrets
aws cloudformation describe-stacks --stack-name rekognition-beta-stack \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" --output text

aws cloudformation describe-stacks --stack-name rekognition-prod-stack \
  --query "Stacks[0].Outputs[?OutputKey=='LambdaArn'].OutputValue" --output text
```

---

## Verifying Results

```bash
aws dynamodb scan --table-name beta_results
aws dynamodb scan --table-name prod_results
```
