"""
analyze_image.py — Amazon Nova 2 Lite Multimodal Image Analysis Pipeline
-------------------------------------------------------------------------
Replaces Amazon Rekognition with Amazon Nova 2 Lite (via Bedrock Converse API).

Instead of a fixed list of detected labels, Nova 2 Lite returns rich, structured
analysis: object descriptions, scene context, educational relevance, content
moderation signals, and suggested tags — all in one model call.

HOW IT WORKS:
  1. Upload each image from images/ to S3 under nova-input/{filename}
  2. Pass the S3 URI directly to Nova 2 Lite via the Bedrock Converse API
  3. Nova returns a structured JSON analysis (parsed from its text response)
  4. Write the result to a branch-specific DynamoDB table

WHY NOVA 2 LITE OVER REKOGNITION:
  - Understands context, not just objects ("a student raising their hand in a
    classroom" vs just ["Person", "Hand", "Room"])
  - Returns educational relevance, tone, and suggested course tags
  - Handles OCR, scene description, and moderation in a single call
  - Fully customizable via system prompt — no retraining needed
  - Supports images up to 2 GB via S3 URI

REQUIRED ENV VARS:
  S3_BUCKET         — S3 bucket name
  DYNAMODB_TABLE    — DynamoDB table (beta_results or prod_results)
  BRANCH            — Git branch name
  AWS_REGION        — defaults to us-east-1

REQUIRED IAM PERMISSIONS:
  bedrock:InvokeModel  on  us.amazon.nova-2-lite-v1:0
  s3:PutObject         on  your bucket
  s3:GetObject         on  your bucket (Bedrock reads the image via S3 URI)
  dynamodb:PutItem     on  your table
"""

import boto3
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET      = os.environ["S3_BUCKET"]
DYNAMODB_TABLE = os.environ["DYNAMODB_TABLE"]
BRANCH         = os.environ.get("BRANCH", "unknown")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
S3_PREFIX      = "nova-input"
IMAGES_DIR     = Path(__file__).parent / "images"
MODEL_ID       = "us.amazon.nova-2-lite-v1:0"
# ─────────────────────────────────────────────────────────────────────────────

s3_client     = boto3.client("s3", region_name=AWS_REGION)
bedrock       = boto3.client("bedrock-runtime", region_name=AWS_REGION)
dynamo        = boto3.resource("dynamodb", region_name=AWS_REGION)
table         = dynamo.Table(DYNAMODB_TABLE)

# System prompt instructs Nova to return structured JSON analysis
SYSTEM_PROMPT = """
You are an AI content analyst for Pixel Learning Co., an educational platform.
When given an image, analyze it and respond ONLY with a valid JSON object using
this exact structure — no markdown, no explanation, just the JSON:

{
  "description": "One sentence describing the image",
  "scene": "Type of scene (e.g. classroom, outdoor, diagram, screenshot)",
  "objects": ["list", "of", "key", "objects"],
  "educational_relevance": "How this image could be used in a course (or 'not applicable')",
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "moderation": {
    "safe": true,
    "flags": []
  },
  "confidence": "high | medium | low"
}
""".strip()


def upload_to_s3(local_path: Path) -> str:
    """Upload image to S3 and return the S3 key."""
    s3_key = f"{S3_PREFIX}/{local_path.name}"
    ext    = local_path.suffix.lower().lstrip(".")
    content_type = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    s3_client.upload_file(
        str(local_path), S3_BUCKET, s3_key,
        ExtraArgs={"ContentType": content_type},
    )
    print(f"  Uploaded s3://{S3_BUCKET}/{s3_key}")
    return s3_key


def analyze_with_nova(s3_key: str, filename: str) -> dict:
    """
    Send the image to Nova 2 Lite via Bedrock Converse API using an S3 URI.
    Nova reads the image directly from S3 — no base64 encoding needed.
    """
    ext    = Path(filename).suffix.lower().lstrip(".")
    fmt    = "jpeg" if ext in ("jpg", "jpeg") else "png"
    s3_uri = f"s3://{S3_BUCKET}/{s3_key}"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "image": {
                        "format": fmt,
                        "source": {
                            "s3Location": {
                                "uri": s3_uri,
                            }
                        },
                    }
                },
                {
                    "text": "Analyze this educational image and return the structured JSON."
                },
            ],
        }
    ]

    response = bedrock.converse(
        modelId=MODEL_ID,
        system=[{"text": SYSTEM_PROMPT}],
        messages=messages,
        inferenceConfig={
            "maxTokens": 512,
            "temperature": 0.2,   # low temp = more consistent structured output
            "topP": 0.9,
        },
    )

    raw_text = response["output"]["message"]["content"][0]["text"].strip()

    # Strip markdown code fences if Nova wraps the JSON anyway
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: store raw text if JSON parsing fails
        print(f"  Warning: Nova response was not valid JSON, storing raw text.")
        return {"raw_response": raw_text}


def write_to_dynamodb(filename: str, s3_key: str, analysis: dict) -> None:
    """Write the Nova analysis result to DynamoDB."""
    item = {
        "filename":    s3_key,
        "analysis":    analysis,
        "timestamp":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch":      BRANCH,
        "source_file": filename,
        "model":       MODEL_ID,
    }
    table.put_item(Item=item)
    print(f"  Written to DynamoDB table '{DYNAMODB_TABLE}'")


def analyze(image_path: Path) -> None:
    print(f"\nAnalyzing: {image_path.name}")
    s3_key   = upload_to_s3(image_path)
    analysis = analyze_with_nova(s3_key, image_path.name)

    print(f"  Description: {analysis.get('description', 'N/A')}")
    print(f"  Tags:        {analysis.get('suggested_tags', [])}")
    print(f"  Safe:        {analysis.get('moderation', {}).get('safe', 'N/A')}")

    write_to_dynamodb(image_path.name, s3_key, analysis)


if __name__ == "__main__":
    images = list(IMAGES_DIR.glob("*.jpg")) + \
             list(IMAGES_DIR.glob("*.jpeg")) + \
             list(IMAGES_DIR.glob("*.png"))

    if not images:
        print(f"No images found in {IMAGES_DIR}. Add .jpg or .png files to images/.")
        raise SystemExit(1)

    print(f"Found {len(images)} image(s).")
    print(f"Model:  {MODEL_ID}")
    print(f"Table:  {DYNAMODB_TABLE}")
    print(f"Branch: {BRANCH}")

    for img in images:
        analyze(img)

    print("\nDone.")
