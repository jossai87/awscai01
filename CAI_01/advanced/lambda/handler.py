# handler.py — Lambda function triggered by API Gateway POST /synthesize
#
# Receives { "text": "..." } in the request body, calls Polly, uploads MP3 to S3.
# Same Polly logic as foundational/synthesize.py — the difference is the wrapper:
# this runs as a Lambda function behind an API Gateway endpoint.
#
# Env vars (set on the Lambda function, not locally):
#   ENVIRONMENT    — "beta" or "prod" (controls the S3 path)
#   S3_BUCKET_NAME — target S3 bucket

import boto3
import json
import os
from datetime import datetime, timezone


def lambda_handler(event, context):
    # Read config from Lambda environment variables
    environment = os.environ.get("ENVIRONMENT", "beta")
    bucket = os.environ["S3_BUCKET_NAME"]

    # Parse the JSON body from the API Gateway event
    body = json.loads(event.get("body") or "{}")
    text = body.get("text", "").strip()

    # Return 400 if no text was provided
    if not text:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing 'text' in request body"}),
        }

    # Call Polly — boto3 uses the Lambda execution role for credentials automatically
    polly = boto3.client("polly")
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Joanna",
        Engine="neural",
    )

    # Read audio bytes and build a timestamped S3 key so each file is unique
    audio = response["AudioStream"].read()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"polly-audio/{environment}/{timestamp}.mp3"

    # Upload to S3
    s3 = boto3.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=audio, ContentType="audio/mpeg")

    # Return the S3 key so the caller knows where the file landed
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Audio synthesized", "s3_key": key}),
    }
