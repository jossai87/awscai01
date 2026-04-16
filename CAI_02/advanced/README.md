# Advanced: Event-Driven Rekognition Pipeline (Lambda + S3 Triggers)

GitHub Actions uploads images to S3, which triggers Lambda functions that run Rekognition and write to DynamoDB. No direct Rekognition calls from CI.

```
GitHub Actions  →  S3 upload (rekognition-input/beta/ or /prod/)
                       ↓  S3 event trigger
                   Lambda (rekognition-beta-handler / rekognition-prod-handler)
                       ↓
                   Rekognition detect_labels  →  DynamoDB (beta_results / prod_results)
```

---

## AWS Resources Required

### S3 Bucket
Same bucket as foundational. Configure two S3 event notifications:

| Prefix                    | Event Type        | Lambda Target                  |
|---------------------------|-------------------|--------------------------------|
| `rekognition-input/beta/` | `s3:ObjectCreated:*` | `rekognition-beta-handler`  |
| `rekognition-input/prod/` | `s3:ObjectCreated:*` | `rekognition-prod-handler`  |

### Lambda Functions
Create two Lambda functions manually (or via the complex IaC tier):

| Function Name               | Runtime     | Handler                    | Env Var                        |
|-----------------------------|-------------|----------------------------|--------------------------------|
| `rekognition-beta-handler`  | Python 3.11 | `beta_handler.lambda_handler` | `DYNAMODB_TABLE=beta_results` |
| `rekognition-prod-handler`  | Python 3.11 | `prod_handler.lambda_handler` | `DYNAMODB_TABLE=prod_results` |

### Lambda Execution Role
Attach a role with:
- `rekognition:DetectLabels`
- `s3:GetObject` scoped to your bucket
- `dynamodb:PutItem` scoped to `beta_results` and `prod_results`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### DynamoDB Tables
Same as foundational: `beta_results` and `prod_results` with `filename` as partition key.

---

## GitHub Secrets

Same secrets as foundational, plus the workflows use `DYNAMODB_TABLE_BETA` and `DYNAMODB_TABLE_PROD` for the validation step.

| Secret Name             | Value             |
|-------------------------|-------------------|
| `AWS_ACCESS_KEY_ID`     | IAM access key    |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key    |
| `AWS_REGION`            | e.g. `us-east-1`  |
| `S3_BUCKET`             | Your bucket name  |
| `DYNAMODB_TABLE_BETA`   | `beta_results`    |
| `DYNAMODB_TABLE_PROD`   | `prod_results`    |

The IAM user also needs `lambda:UpdateFunctionCode` and `lambda:GetFunction`.

---

## How It Works

1. Add images to `CAI_02/foundational/images/`
2. Open a PR → workflow uploads to `rekognition-input/beta/` → S3 triggers `rekognition-beta-handler` → results in `beta_results`
3. Merge → workflow uploads to `rekognition-input/prod/` → S3 triggers `rekognition-prod-handler` → results in `prod_results`
4. The validation step polls DynamoDB for up to 60 seconds to confirm the Lambda ran successfully
