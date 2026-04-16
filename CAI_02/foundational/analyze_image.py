"""
analyze_image.py — Amazon Rekognition Image Labeling Pipeline
-------------------------------------------------------------
For each image in the images/ folder:
  1. Uploads the image to S3 under rekognition-input/{filename}
  2. Calls Rekognition detect_labels on the uploaded object
  3. Writes the result to a DynamoDB table (branch-specific)

REQUIRED ENV VARS:
  S3_BUCKET         — S3 bucket name
  DYNAMODB_TABLE    — DynamoDB table name (beta_results or prod_results)
  BRANCH            — Git branch name (used as metadata in the record)
  AWS_REGION        — AWS region (default: us-east-1)
"""

import boto3
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET      = os.environ["S3_BUCKET"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
BRANCH         = os.environ.get("BRANCH", "unknown")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
S3_PREFIX      = "rekognition-input"
IMAGES_DIR     = Path(__file__).parent / "images"
MAX_LABELS     = 10
MIN_CONFIDENCE = 70.0
# ─────────────────────────────────────────────────────────────────────────────

s3_client   = boto3.client("s3",       region_name=AWS_REGION)
rek_client  = boto3.client("rekognition", region_name=AWS_REGION)
dynamo      = boto3.resource("dynamodb", region_name=AWS_REGION)
table       = dynamo.Table(DYNAMODB_TABLE)


def upload_to_s3(local_path: Path) -> str:
    """Upload image to S3 and return the S3 key."""
    s3_key = f"{S3_PREFIX}/{local_path.name}"
    s3_client.upload_file(
        str(local_path),
        S3_BUCKET,
        s3_key,
        ExtraArgs={"ContentType": "image/jpeg"},
    )
    print(f"  Uploaded s3://{S3_BUCKET}/{s3_key}")
    return s3_key


def detect_labels(s3_key: str) -> list[dict]:
    """Run Rekognition detect_labels on an S3 object."""
    response = rek_client.detect_labels(
        Image={"S3Object": {"Bucket": S3_BUCKET, "Name": s3_key}},
        MaxLabels=MAX_LABELS,
        MinConfidence=MIN_CONFIDENCE,
    )
    return [
        {"Name": label["Name"], "Confidence": round(label["Confidence"], 2)}
        for label in response["Labels"]
    ]


def write_to_dynamodb(filename: str, s3_key: str, labels: list[dict]) -> None:
    """Write analysis result to DynamoDB."""
    item = {
        "filename":  s3_key,
        "labels":    labels,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch":    BRANCH,
        "source_file": filename,
    }
    table.put_item(Item=item)
    print(f"  Written to DynamoDB table '{DYNAMODB_TABLE}'")
    print(f"  Labels: {json.dumps(labels, indent=2)}")


def analyze(image_path: Path) -> None:
    print(f"\nAnalyzing: {image_path.name}")
    s3_key = upload_to_s3(image_path)
    labels = detect_labels(s3_key)
    write_to_dynamodb(image_path.name, s3_key, labels)


if __name__ == "__main__":
    images = list(IMAGES_DIR.glob("*.jpg")) + list(IMAGES_DIR.glob("*.png"))
    if not images:
        print(f"No images found in {IMAGES_DIR}. Add .jpg or .png files to images/.")
        raise SystemExit(1)

    print(f"Found {len(images)} image(s). Table: {DYNAMODB_TABLE} | Branch: {BRANCH}")
    for img in images:
        analyze(img)

    print("\nDone.")
