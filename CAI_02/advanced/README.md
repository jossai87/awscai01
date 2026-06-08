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

## Step-by-Step Deployment

### Step 1: Create an S3 Bucket

Go to AWS Console → S3 → Create bucket. Any name, any region. Note the bucket name — you'll use it throughout.

---

### Step 2: Create DynamoDB Tables

Go to AWS Console → DynamoDB → Create table. Create both tables:

| Table Name     | Partition Key       | Billing Mode    |
|----------------|---------------------|-----------------|
| `beta_results` | `filename` (String) | PAY_PER_REQUEST |
| `prod_results` | `filename` (String) | PAY_PER_REQUEST |

---

### Step 3: Create the Lambda Execution Role

Go to AWS Console → IAM → Roles → Create role.

1. Choose **AWS service** → **Lambda**
2. Attach an inline policy with these permissions (replace `your-bucket` and `your-region`/`your-account-id` with real values, or use `*` to keep it simple):

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "rekognition:DetectLabels",
    "dynamodb:PutItem",
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": "*"
}
```

3. Name the role something like `rekognition-lambda-role`

---

### Step 4: Create the Lambda Functions

Go to AWS Console → Lambda → Create function.

Create **two functions** with these settings:

| Setting          | Beta Function                    | Prod Function                    |
|------------------|----------------------------------|----------------------------------|
| Function name    | `rekognition-beta-handler`       | `rekognition-prod-handler`       |
| Runtime          | Python 3.11                      | Python 3.11                      |
| Handler          | `beta_handler.lambda_handler`    | `prod_handler.lambda_handler`    |
| Execution role   | `rekognition-lambda-role`        | `rekognition-lambda-role`        |

For each function, add an environment variable:

| Function                   | Key              | Value          |
|----------------------------|------------------|----------------|
| `rekognition-beta-handler` | `DYNAMODB_TABLE` | `beta_results` |
| `rekognition-prod-handler` | `DYNAMODB_TABLE` | `prod_results` |

Upload the code from `CAI_02/advanced/lambda/` — `beta_handler.py` to the beta function and `prod_handler.py` to the prod function.

---

### Step 5: Configure S3 Event Notifications

Go to AWS Console → S3 → your bucket → **Properties** → **Event notifications** → **Create event notification**.

Create two notifications:

| Notification Name  | Prefix                      | Event type            | Destination                    |
|--------------------|-----------------------------|-----------------------|--------------------------------|
| `beta-trigger`     | `rekognition-input/beta/`   | `s3:ObjectCreated:*`  | `rekognition-beta-handler`     |
| `prod-trigger`     | `rekognition-input/prod/`   | `s3:ObjectCreated:*`  | `rekognition-prod-handler`     |

> You'll need to grant S3 permission to invoke each Lambda. AWS will prompt you to do this automatically when you set up the notification, or you can add a resource-based policy manually via Lambda → Configuration → Permissions.

---

### Step 6: Create an IAM User for GitHub Actions

Go to AWS Console → IAM → Users → Create user.

1. Name it something like `rekognition-github-actions`
2. Attach an inline policy:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "lambda:UpdateFunctionCode",
    "lambda:GetFunction",
    "dynamodb:Scan"
  ],
  "Resource": "*"
}
```

3. Go to **Security credentials** → **Create access key** → choose **Application running outside AWS**
4. Save the **Access Key ID** and **Secret Access Key**

---

### Step 7: Add GitHub Secrets

Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add all five secrets:

| Secret Name             | Value                         |
|-------------------------|-------------------------------|
| `AWS_ACCESS_KEY_ID`     | From the IAM user you created |
| `AWS_SECRET_ACCESS_KEY` | From the IAM user you created |
| `AWS_REGION`            | e.g. `us-east-1`              |
| `S3_BUCKET`             | Your S3 bucket name           |
| `DYNAMODB_TABLE_BETA`   | `beta_results`                |
| `DYNAMODB_TABLE_PROD`   | `prod_results`                |

---

### Step 8: Add an Image and Open a Pull Request

Add a `.jpg` or `.png` to `CAI_02/foundational/images/`, then push to a new branch:

```bash
git checkout -b feature/test-rekognition
git add CAI_02/foundational/images/
git commit -m "add image for rekognition analysis"
git push -u origin feature/test-rekognition
```

Open a pull request from `feature/test-rekognition` → `main` on GitHub.

The **beta workflow** triggers automatically — it uploads the image to `rekognition-input/beta/`, which fires the S3 event and invokes `rekognition-beta-handler`. Watch it under the **Actions** tab.

The workflow polls DynamoDB for up to 60 seconds to confirm the Lambda ran successfully.

---

### Step 9: Verify Beta Results

```bash
aws dynamodb scan --table-name beta_results
```

---

### Step 10: Merge to Trigger Prod

Merge the pull request. The **prod workflow** triggers automatically, uploading to `rekognition-input/prod/` and invoking `rekognition-prod-handler`.

```bash
aws dynamodb scan --table-name prod_results
```

---

## Local Setup

To provision all AWS resources locally instead of through GitHub Actions, use the setup script.

**Set up a virtual environment and install dependencies:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install boto3
```

**Run the setup script:**

```bash
S3_BUCKET=cai-01-jossai-1 \
AWS_REGION=us-east-1 \
python3 CAI_02/advanced/scripts/setup_advanced.py
```

The script will create the DynamoDB tables, Lambda functions, S3 event notifications, and CI IAM user, then print all the GitHub secrets you need.

---

## AWS Resources Reference

### S3 Bucket
Same bucket as foundational. Configure two S3 event notifications:

| Prefix                    | Event Type           | Lambda Target                  |
|---------------------------|----------------------|--------------------------------|
| `rekognition-input/beta/` | `s3:ObjectCreated:*` | `rekognition-beta-handler`     |
| `rekognition-input/prod/` | `s3:ObjectCreated:*` | `rekognition-prod-handler`     |

### Lambda Functions

| Function Name               | Runtime     | Handler                          | Env Var                        |
|-----------------------------|-------------|----------------------------------|--------------------------------|
| `rekognition-beta-handler`  | Python 3.11 | `beta_handler.lambda_handler`    | `DYNAMODB_TABLE=beta_results`  |
| `rekognition-prod-handler`  | Python 3.11 | `prod_handler.lambda_handler`    | `DYNAMODB_TABLE=prod_results`  |

### Lambda Execution Role
Attach a role with:
- `rekognition:DetectLabels`
- `s3:GetObject` scoped to your bucket
- `dynamodb:PutItem` scoped to `beta_results` and `prod_results`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### DynamoDB Tables
Same as foundational: `beta_results` and `prod_results` with `filename` as partition key.

---

## GitHub Secrets Reference

| Secret Name             | Value             |
|-------------------------|-------------------|
| `AWS_ACCESS_KEY_ID`     | IAM access key    |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key    |
| `AWS_REGION`            | e.g. `us-east-1`  |
| `S3_BUCKET`             | Your bucket name  |
| `DYNAMODB_TABLE_BETA`   | `beta_results`    |
| `DYNAMODB_TABLE_PROD`   | `prod_results`    |

The IAM user also needs `lambda:UpdateFunctionCode` and `lambda:GetFunction`.
