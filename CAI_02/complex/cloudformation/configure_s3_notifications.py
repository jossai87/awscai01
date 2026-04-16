"""
configure_s3_notifications.py
------------------------------
Adds (or updates) S3 event notification rules so that uploads to
  rekognition-input/beta/  →  rekognition-beta-handler Lambda
  rekognition-input/prod/  →  rekognition-prod-handler Lambda

Run after both CloudFormation stacks are deployed.

Usage:
  python configure_s3_notifications.py

Required env vars:
  S3_BUCKET          — bucket name
  BETA_LAMBDA_ARN    — ARN of rekognition-beta-handler
  PROD_LAMBDA_ARN    — ARN of rekognition-prod-handler
  AWS_REGION         — AWS region
"""

import boto3
import os

S3_BUCKET       = os.environ["S3_BUCKET"]
BETA_LAMBDA_ARN = os.environ["BETA_LAMBDA_ARN"]
PROD_LAMBDA_ARN = os.environ["PROD_LAMBDA_ARN"]
AWS_REGION      = os.environ.get("AWS_REGION", "us-east-1")

s3 = boto3.client("s3", region_name=AWS_REGION)

notification_config = {
    "LambdaFunctionConfigurations": [
        {
            "Id": "RekognitionBetaTrigger",
            "LambdaFunctionArn": BETA_LAMBDA_ARN,
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": "rekognition-input/beta/"},
                        {"Name": "suffix", "Value": ".jpg"},
                    ]
                }
            },
        },
        {
            "Id": "RekognitionBetaTriggerPng",
            "LambdaFunctionArn": BETA_LAMBDA_ARN,
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": "rekognition-input/beta/"},
                        {"Name": "suffix", "Value": ".png"},
                    ]
                }
            },
        },
        {
            "Id": "RekognitionProdTrigger",
            "LambdaFunctionArn": PROD_LAMBDA_ARN,
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": "rekognition-input/prod/"},
                        {"Name": "suffix", "Value": ".jpg"},
                    ]
                }
            },
        },
        {
            "Id": "RekognitionProdTriggerPng",
            "LambdaFunctionArn": PROD_LAMBDA_ARN,
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": "rekognition-input/prod/"},
                        {"Name": "suffix", "Value": ".png"},
                    ]
                }
            },
        },
    ]
}

s3.put_bucket_notification_configuration(
    Bucket=S3_BUCKET,
    NotificationConfiguration=notification_config,
)
print(f"S3 event notifications configured on bucket: {S3_BUCKET}")
