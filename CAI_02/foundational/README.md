# Foundational: Amazon Rekognition Image Labeling Pipeline

Automatically classifies images using Amazon Rekognition and logs results to branch-specific DynamoDB tables via GitHub Actions.

```
images/*.jpg|png  →  S3 (rekognition-input/)  →  Rekognition detect_labels  →  DynamoDB
```

---

## Step-by-Step Deployment

### Step 1: Create AWS Resources

**S3 Bucket**

Go to the AWS Console → S3 → Create bucket. Any name, any region. No special configuration needed. Note the bucket name for later.

**DynamoDB Tables**

Go to AWS Console → DynamoDB → Create table. Create both tables:

| Table Name     | Partition Key        | Billing Mode    |
|----------------|----------------------|-----------------|
| `beta_results` | `filename` (String)  | PAY_PER_REQUEST |
| `prod_results` | `filename` (String)  | PAY_PER_REQUEST |

**IAM User**

Go to AWS Console → IAM → Users → Create user.
1. Give it a name (e.g. `rekognition-github-actions`)
2. Attach a custom inline policy with these permissions:

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

3. After creating the user, go to **Security credentials** → **Create access key** → choose **Application running outside AWS**
4. Save the **Access Key ID** and **Secret Access Key** — you'll need them in the next step

---

### Step 2: Add GitHub Secrets

Go to your repo on GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.

Add all six secrets:

| Secret Name             | Value                        |
|-------------------------|------------------------------|
| `AWS_ACCESS_KEY_ID`     | From the IAM user you created |
| `AWS_SECRET_ACCESS_KEY` | From the IAM user you created |
| `AWS_REGION`            | e.g. `us-east-1`             |
| `S3_BUCKET`             | Your S3 bucket name          |
| `DYNAMODB_TABLE_BETA`   | `beta_results`               |
| `DYNAMODB_TABLE_PROD`   | `prod_results`               |

---

### Step 3: Add an Image

Add a `.jpg` or `.png` file to the `CAI_02/foundational/images/` folder. There's already a sample image there you can use.

---

### Step 4: Create a Branch and Open a Pull Request

```bash
git checkout -b feature/test-rekognition3
git add CAI_02/foundational/images/
git commit -m "add image for rekognition analysis"
git push -u origin feature/test-rekognition3
```

Then go to GitHub and open a pull request from `feature/test-rekognition` → `main`.

The **beta workflow** will trigger automatically. Watch it run under the **Actions** tab.

---

### Step 5: Verify Beta Results

Once the workflow completes, check DynamoDB:

**AWS Console:**
1. Open DynamoDB → Tables → `beta_results`
2. Click "Explore table items"

**CLI:**
```bash
aws dynamodb scan --table-name beta_results
```

---

### Step 6: Merge to Trigger Prod

Merge the pull request on GitHub. The **prod workflow** will trigger automatically and write results to `prod_results`.

```bash
aws dynamodb scan --table-name prod_results
```

---

## AWS Resources Reference

### S3 Bucket
Any bucket in your target region. No special configuration needed.

### DynamoDB Tables

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

## Example DynamoDB Record

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

---

## Local Run

To run the pipeline locally without GitHub Actions:

**Set up a virtual environment and install dependencies:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install boto3
```

**Run the script:**

```bash
S3_BUCKET=cai-01-jossai-1 \
DYNAMODB_TABLE=beta_results \
BRANCH=feature/test-rekognition3 \
python3 CAI_02/foundational/analyze_image.py
```

Replace `your-bucket-name` with your actual S3 bucket. Change `DYNAMODB_TABLE` to `prod_results` to write to the prod table instead.