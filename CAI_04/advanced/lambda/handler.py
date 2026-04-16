"""
handler.py — Event-Driven Prompt Pipeline Lambda
-------------------------------------------------
Triggered by S3 uploads to prompt_inputs/*.json.
Reads env from object metadata ({"env": "beta"}) or filename prefix.

Pipeline:
  1. Download prompt config JSON from S3
  2. Download template file from S3 (prompt_templates/{template})
  3. Render prompt with variables
  4. Invoke Bedrock (Claude 3 Sonnet, on-demand)
  5. Upload output HTML/MD to S3 under {env}/outputs/

Required Lambda environment variables:
  S3_BUCKET   — bucket for all inputs and outputs
  AWS_REGION  — AWS region
"""

import boto3
import json
import os
import urllib.parse

S3_BUCKET  = os.environ["S3_BUCKET"]
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID   = "anthropic.claude-3-sonnet-20240229-v1:0"
MAX_TOKENS = 1024

s3      = boto3.client("s3",              region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def get_env(bucket: str, key: str, filename: str) -> str:
    try:
        meta = s3.head_object(Bucket=bucket, Key=key).get("Metadata", {})
        if meta.get("env") in ("beta", "prod"):
            return meta["env"]
    except Exception:
        pass
    return "prod" if filename.startswith("prod-") else "beta"


def load_config(bucket: str, key: str) -> dict:
    obj = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj["Body"].read())


def load_template(config: dict) -> str:
    template_key = f"prompt_templates/{config['template']}"
    obj = s3.get_object(Bucket=S3_BUCKET, Key=template_key)
    return obj["Body"].read().decode("utf-8")


def render_prompt(template: str, variables: dict) -> str:
    return template.format(**variables)


def invoke_bedrock(prompt: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": f"Human: {prompt}"}],
    }
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def upload_output(env: str, config: dict, content: str):
    fmt          = config.get("output_format", "html")
    filename     = f"{config['output_filename']}.{fmt}"
    s3_key       = f"{env}/outputs/{filename}"
    content_type = "text/html" if fmt == "html" else "text/markdown"
    s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=content.encode(), ContentType=content_type)
    print(f"Uploaded: s3://{S3_BUCKET}/{s3_key}")


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket   = record["s3"]["bucket"]["name"]
        key      = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        filename = key.split("/")[-1]
        env      = get_env(bucket, key, filename)

        print(f"[{env}] Processing s3://{bucket}/{key}")

        config   = load_config(bucket, key)
        template = load_template(config)
        prompt   = render_prompt(template, config.get("variables", {}))
        response = invoke_bedrock(prompt)
        upload_output(env, config, response)

    return {"statusCode": 200, "body": "OK"}
