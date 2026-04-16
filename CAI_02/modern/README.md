# Modern: Amazon Nova 2 Lite Multimodal Image Analysis Pipeline

Replaces Amazon Rekognition with **Amazon Nova 2 Lite** — a foundation model on Amazon Bedrock — for richer, context-aware image understanding.

```
images/*.jpg|png  →  S3 (nova-input/)  →  Nova 2 Lite (Bedrock Converse API)  →  DynamoDB
```

---

## Why Nova 2 Lite Instead of Rekognition

| | Amazon Rekognition | Amazon Nova 2 Lite |
|---|---|---|
| Output | Fixed label list with confidence scores | Rich structured JSON: description, scene, objects, educational relevance, tags, moderation |
| Customizable? | No | Yes — via system prompt, no retraining |
| Context-aware? | No | Yes ("student raising hand in classroom" vs just "Person, Hand, Room") |
| OCR built-in? | Separate API call | Yes, in the same call |
| Moderation | Separate API call | Yes, in the same call |
| Input method | S3 key | S3 URI or raw bytes |
| Model type | Rule-based CV service | Foundation model (multimodal LLM) |

### Example Output

Rekognition returns:
```json
[{"Name": "Person", "Confidence": 98.1}, {"Name": "Classroom", "Confidence": 94.3}]
```

Nova 2 Lite returns:
```json
{
  "description": "A teacher writing on a whiteboard in front of a group of students",
  "scene": "classroom",
  "objects": ["whiteboard", "teacher", "students", "desks", "markers"],
  "educational_relevance": "Suitable for courses on teaching methods or classroom management",
  "suggested_tags": ["education", "classroom", "teaching", "learning", "students"],
  "moderation": {"safe": true, "flags": []},
  "confidence": "high"
}
```

---

## AWS Resources Required

### Enable Nova 2 Lite in Bedrock
1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in the left sidebar
3. Find "Amazon Nova Lite" and request access (usually instant)

**Supported regions:** `us-east-1`, `us-west-2`, `eu-west-1`, `ap-northeast-1`

### S3 Bucket
Same bucket used in other tiers. Nova reads images directly via S3 URI — no base64 encoding needed for large files.

### DynamoDB Tables
Same as foundational: `beta_results` and `prod_results` with `filename` as partition key.

### IAM Permissions
The user or role running this pipeline needs:

```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "s3:PutObject",
    "s3:GetObject",
    "dynamodb:PutItem"
  ],
  "Resource": "*"
}
```

> `s3:GetObject` is required because Bedrock fetches the image from S3 on your behalf using the S3 URI you pass in the request.

---

## GitHub Secrets

| Secret Name             | Description                  |
|-------------------------|------------------------------|
| `AWS_ACCESS_KEY_ID`     | IAM access key               |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key               |
| `AWS_REGION`            | Must be a Nova-supported region (e.g. `us-east-1`) |
| `S3_BUCKET`             | Your S3 bucket name          |
| `DYNAMODB_TABLE_BETA`   | `beta_results`               |
| `DYNAMODB_TABLE_PROD`   | `prod_results`               |

---

## Adding and Analyzing Images

1. Add `.jpg` or `.png` files to `CAI_02/modern/images/`
2. Open a pull request → beta workflow runs → results written to `beta_results`
3. Merge → prod workflow runs → results written to `prod_results`

---

## Verifying Results in DynamoDB

```bash
aws dynamodb scan --table-name beta_results
aws dynamodb scan --table-name prod_results
```

Each record includes the full Nova analysis under the `analysis` key, plus `model`, `branch`, `timestamp`, and `filename`.

---

## How the Code Works

`analyze_image.py` does three things per image:

1. `upload_to_s3()` — uploads the image and returns the S3 key
2. `analyze_with_nova()` — calls `bedrock.converse()` with the S3 URI and a structured system prompt that instructs Nova to return JSON
3. `write_to_dynamodb()` — stores the parsed analysis alongside metadata

The system prompt is the key lever — you can extend it to add sentiment, language detection, accessibility descriptions, or any other classification your content team needs, without touching any AWS infrastructure.
