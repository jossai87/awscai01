# Foundational: Amazon Rekognition Image Labeling Pipeline

Automatically classifies images using Amazon Rekognition and logs results to branch-specific DynamoDB tables via GitHub Actions.

```
images/*.jpg|png  →  S3 (rekognition-input/)  →  Rekognition detect_labels  →  DynamoDB
```

---

## AWS Resources Required

Create these before running the workflows:

### S3 Bucket
Any bucket in your target region. No special configuration needed.

### DynamoDB Tables
Create two tables with the following settings:

| Table Name     | Partition Key        | Type   |
|----------------|----------------------|--------|
| `beta_results` | `filename` (String)  | String |
| `prod_results` | `filename` (String)  | String |

Use on-demand (PAY_PER_REQUEST) billing mode.

### IAM User / Role
Create an IAM user with the following permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "rekognition:DetectLabels",
    "dynamodb:PutItem"
  ],
  "Resource": "*"
}
```

---

## GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret Name          | Description                          |
|----------------------|--------------------------------------|
| `AWS_ACCESS_KEY_ID`  | IAM user access key                  |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key               |
| `AWS_REGION`         | e.g. `us-east-1`                     |
| `S3_BUCKET`          | Your S3 bucket name                  |
| `DYNAMODB_TABLE_BETA`| `beta_results`                       |
| `DYNAMODB_TABLE_PROD`| `prod_results`                       |

---

## Adding and Analyzing Images

1. Add `.jpg` or `.png` files to the `CAI_02/foundational/images/` folder.
2. Open a pull request targeting `main` → beta workflow runs → results written to `beta_results`.
3. Merge the PR → prod workflow runs → results written to `prod_results`.

---

## Verifying Results in DynamoDB

Via AWS Console:
1. Open DynamoDB → Tables → `beta_results` or `prod_results`
2. Click "Explore table items"

Via CLI:

**macOS / Linux**
```bash
aws dynamodb scan --table-name beta_results
aws dynamodb scan --table-name prod_results
```

**Windows (PowerShell)**
```powershell
aws dynamodb scan --table-name beta_results
aws dynamodb scan --table-name prod_results
```

### Example Record

```json
{
  "filename": "rekognition-input/classroom.jpg",
  "labels": [
    {"Name": "Classroom", "Confidence": 99.1},
    {"Name": "Person",    "Confidence": 97.4}
  ],
  "timestamp": "2025-06-01T14:55:32Z",
  "branch": "feature/add-images",
  "source_file": "classroom.jpg"
}
```
