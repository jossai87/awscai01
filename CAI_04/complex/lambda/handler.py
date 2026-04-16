"""
handler.py — Unified Prompt Pipeline Lambda (Complex tier)
----------------------------------------------------------
Triggered by S3 uploads to prompt_inputs/*.json.
ENV and S3_BUCKET set by CloudFormation as Lambda environment variables.

Required Lambda environment variables:
  S3_BUCKET  — set by CloudFormation
  ENV        — beta or prod (set by CloudFormation)
  AWS_REGION — AWS region
"""

import boto3
import json
import os
import urllib.parse

S3_BUCKET  = os.environ["S3_BUCKET"]
ENV        = os.environ.get("ENV", "beta")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID   = "anthropic.claude-3-sonnet-20240229-v1:0"
MAX_TOKENS = 1024

s3      = boto3.client("s3",              region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def load_config(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def load_template(config: dict) -> str:
    key = f"prompt_templates/{config['template']}"
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


def invoke_bedrock(prompt: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": f"Human: {prompt}"}],
    }
    response = bedrock.invoke_model(
        modelId=MODEL_ID, body=json.dumps(body),
        contentType="application/json", accept="application/json",
    )
    return json.loads(response["body"].read())["content"][0]["text"]


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket   = record["s3"]["bucket"]["name"]
        key      = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        filename = key.split("/")[-1]

        print(f"[{ENV}] Processing s3://{bucket}/{key}")

        config   = load_config(bucket, key)
        template = load_template(config)
        prompt   = template.format(**config.get("variables", {}))
        response = invoke_bedrock(prompt)

        fmt      = config.get("output_format", "html")
        out_name = f"{config['output_filename']}.{fmt}"
        out_key  = f"{ENV}/outputs/{out_name}"
        ct       = "text/html" if fmt == "html" else "text/markdown"

        s3.put_object(Bucket=S3_BUCKET, Key=out_key, Body=response.encode(), ContentType=ct)
        print(f"  Uploaded: s3://{S3_BUCKET}/{out_key}")

    return {"statusCode": 200, "body": "OK"}
