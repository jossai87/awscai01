"""
prod_handler.py — Rekognition Prod Lambda
-----------------------------------------
Triggered by S3 uploads to rekognition-input/prod/.
Detects labels using Rekognition and writes results to prod_results DynamoDB table.

Required Lambda environment variables:
  DYNAMODB_TABLE — prod_results
"""

import boto3
import json
import os
import urllib.parse
from datetime import datetime, timezone

rek_client = boto3.client("rekognition")
dynamo     = boto3.resource("dynamodb")
table      = dynamo.Table(os.environ["DYNAMODB_TABLE"])

MAX_LABELS     = 10
MIN_CONFIDENCE = 70.0


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket   = record["s3"]["bucket"]["name"]
        s3_key   = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        filename = s3_key.split("/")[-1]

        print(f"Processing s3://{bucket}/{s3_key}")

        response = rek_client.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": s3_key}},
            MaxLabels=MAX_LABELS,
            MinConfidence=MIN_CONFIDENCE,
        )

        labels = [
            {"Name": lbl["Name"], "Confidence": round(lbl["Confidence"], 2)}
            for lbl in response["Labels"]
        ]

        item = {
            "filename":  s3_key,
            "labels":    labels,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "branch":    "prod",
            "source_file": filename,
        }

        table.put_item(Item=item)
        print(f"Written to {os.environ['DYNAMODB_TABLE']}: {json.dumps(labels)}")

    return {"statusCode": 200, "body": "OK"}
