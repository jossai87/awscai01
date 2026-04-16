"""
process_prompt.py — Bedrock Prompt Deployment Pipeline
-------------------------------------------------------
For each .json config in prompts/:
  1. Loads the prompt template from prompt_templates/
  2. Renders the template with variables from the config
  3. Sends the rendered prompt to Amazon Bedrock (Claude 3 Sonnet)
  4. Saves the response to outputs/{output_filename}.{format}
  5. Uploads the output to S3 under {ENV}/outputs/{filename}

REQUIRED ENV VARS:
  S3_BUCKET   — S3 bucket name
  ENV         — beta or prod (controls S3 prefix)
  AWS_REGION  — defaults to us-east-1

MODEL:
  anthropic.claude-3-sonnet-20240229-v1:0 (on-demand, no provisioned throughput)
"""

import boto3
import json
import os
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET      = os.environ["S3_BUCKET"]
ENV            = os.environ.get("ENV", "beta")
AWS_REGION     = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID       = "anthropic.claude-3-sonnet-20240229-v1:0"
MAX_TOKENS     = 1024
PROMPTS_DIR    = Path(__file__).parent / "prompts"
TEMPLATES_DIR  = Path(__file__).parent / "prompt_templates"
OUTPUTS_DIR    = Path(__file__).parent / "outputs"
# ─────────────────────────────────────────────────────────────────────────────

OUTPUTS_DIR.mkdir(exist_ok=True)

s3      = boto3.client("s3",              region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return json.load(f)


def render_prompt(config: dict) -> str:
    template_path = TEMPLATES_DIR / config["template"]
    template_text = template_path.read_text()
    return template_text.format(**config.get("variables", {}))


def invoke_bedrock(prompt: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "user", "content": f"Human: {prompt}"}
        ],
    }
    response = bedrock.invoke_model(
        modelId=MODEL_ID,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def save_output(config: dict, content: str) -> Path:
    fmt      = config.get("output_format", "html")
    filename = f"{config['output_filename']}.{fmt}"
    out_path = OUTPUTS_DIR / filename
    out_path.write_text(content, encoding="utf-8")
    print(f"  Saved locally: {out_path}")
    return out_path


def upload_to_s3(local_path: Path) -> str:
    s3_key      = f"{ENV}/outputs/{local_path.name}"
    content_type = "text/html" if local_path.suffix == ".html" else "text/markdown"
    s3.upload_file(
        str(local_path), S3_BUCKET, s3_key,
        ExtraArgs={"ContentType": content_type},
    )
    print(f"  Uploaded: s3://{S3_BUCKET}/{s3_key}")
    return s3_key


def process(config_path: Path) -> None:
    print(f"\nProcessing: {config_path.name}")
    config     = load_config(config_path)
    prompt     = render_prompt(config)
    print(f"  Invoking Bedrock ({MODEL_ID})...")
    response   = invoke_bedrock(prompt)
    local_path = save_output(config, response)
    upload_to_s3(local_path)


if __name__ == "__main__":
    configs = list(PROMPTS_DIR.glob("*.json"))
    if not configs:
        print(f"No .json configs found in {PROMPTS_DIR}.")
        raise SystemExit(1)

    print(f"Found {len(configs)} prompt config(s). ENV={ENV} | Bucket={S3_BUCKET}")
    for cfg in configs:
        process(cfg)
    print("\nDone.")
