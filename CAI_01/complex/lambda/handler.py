# handler.py — same logic as advanced/lambda/handler.py
#
# The difference is how this gets deployed: CloudFormation creates the Lambda
# with placeholder code, then setup_complex.py pushes this file to replace it.
#
# Env vars (set in the CloudFormation template):
#   ENVIRONMENT    — "beta" or "prod"
#   S3_BUCKET_NAME — target S3 bucket
#
# Security note: the beta IAM role (created by CloudFormation) has an explicit
# DENY on polly-audio/prod/*, so even a misconfigured ENVIRONMENT can't write to prod.

import boto3
import json
import os
from datetime import datetime, timezone


def lambda_handler(event, context):
    environment = os.environ.get("ENVIRONMENT", "beta")
    bucket = os.environ["S3_BUCKET_NAME"]

    # Parse the JSON body from the API Gateway event
    body = json.loads(event.get("body") or "{}")
    text = body.get("text", "").strip()

    if not text:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'text' in request body"}),
        }

    # Call Polly — uses the Lambda execution role for credentials automatically
    polly = boto3.client("polly")
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Joanna",
        Engine="neural",
    )

    # Timestamped key keeps each synthesis as a unique file in S3
    audio = response["AudioStream"].read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"polly-audio/{environment}/{timestamp}.mp3"

    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=audio, ContentType="audio/mpeg")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Audio synthesized", "s3_key": key}),
    }
