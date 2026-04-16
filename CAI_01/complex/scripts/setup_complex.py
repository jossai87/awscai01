"""
setup_complex.py — deploys the Polly pipeline via CloudFormation.

Deploys two stacks from cloudformation/:
  - polly-beta-stack  (template-beta.yml)
  - polly-prod-stack  (template-prod.yml)

Each stack provisions: IAM role, Lambda, API Gateway + POST /synthesize.
After both stacks are up, pushes the real handler.py code to both Lambdas
(CloudFormation starts them with placeholder code).

Usage:
  source /tmp/cai01-venv/bin/activate
  export S3_BUCKET_NAME=cai-01-jossai-1
  export AWS_REGION=us-east-1
  python3 setup_complex.py

Safe to re-run — CloudFormation updates existing stacks or skips if nothing changed.
"""

import boto3
import io
import os
import sys
import zipfile
from pathlib import Path

# Config
S3_BUCKET     = os.environ.get("S3_BUCKET_NAME")
AWS_REGION    = os.environ.get("AWS_REGION", "us-east-1")
TEMPLATES_DIR = Path(__file__).parent.parent / "cloudformation"
HANDLER_PATH  = Path(__file__).parent.parent / "lambda" / "handler.py"

STACKS = {
    "beta": {
        "stack_name": "polly-beta-stack",
        "template":   TEMPLATES_DIR / "template-beta.yml",
        "function":   "PollyTextToSpeech_Beta",
        "output_key": "ApiGatewayUrl",
    },
    "prod": {
        "stack_name": "polly-prod-stack",
        "template":   TEMPLATES_DIR / "template-prod.yml",
        "function":   "PollyTextToSpeech_Prod",
        "output_key": "ApiGatewayUrl",
    },
}

if not S3_BUCKET:
    print("Error: S3_BUCKET_NAME environment variable is required.")
    sys.exit(1)

cfn = boto3.client("cloudformation", region_name=AWS_REGION)
lam = boto3.client("lambda",         region_name=AWS_REGION)


def stack_exists(stack_name: str) -> bool:
    try:
        cfn.describe_stacks(StackName=stack_name)
        return True
    except cfn.exceptions.ClientError:
        return False


def deploy_stack(stack_name: str, template_path: Path) -> None:
    """Create or update a CloudFormation stack. Skips gracefully if nothing changed."""
    template_body = template_path.read_text()
    params = [{"ParameterKey": "S3BucketName", "ParameterValue": S3_BUCKET}]
    caps   = ["CAPABILITY_NAMED_IAM"]  # Required when the template creates named IAM resources

    if stack_exists(stack_name):
        print(f"Stack '{stack_name}' exists, updating...")
        try:
            cfn.update_stack(StackName=stack_name, TemplateBody=template_body, Parameters=params, Capabilities=caps)
            waiter = cfn.get_waiter("stack_update_complete")
        except cfn.exceptions.ClientError as e:
            if "No updates are to be performed" in str(e):
                print(f"  No changes — stack already up to date.")
                return
            raise
    else:
        print(f"Creating stack '{stack_name}'...")
        cfn.create_stack(StackName=stack_name, TemplateBody=template_body, Parameters=params, Capabilities=caps)
        waiter = cfn.get_waiter("stack_create_complete")

    print(f"  Waiting for stack to complete...")
    waiter.wait(StackName=stack_name)
    print(f"  Done.")


def get_stack_output(stack_name: str, key: str) -> str:
    """Read a named output value from a deployed stack."""
    resp = cfn.describe_stacks(StackName=stack_name)
    for output in resp["Stacks"][0].get("Outputs", []):
        if output["OutputKey"] == key:
            return output["OutputValue"]
    return ""


def build_zip() -> bytes:
    """Package handler.py into a zip in memory — Lambda requires code as a zip."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(HANDLER_PATH, "handler.py")
    return buf.getvalue()


def deploy_lambda_code(function_name: str, zip_bytes: bytes) -> None:
    """Push the real handler code to a Lambda, replacing the CloudFormation placeholder."""
    print(f"  Deploying handler code to {function_name}...")
    lam.update_function_code(FunctionName=function_name, ZipFile=zip_bytes)
    lam.get_waiter("function_updated").wait(FunctionName=function_name)
    print(f"  Code deployed.")


if __name__ == "__main__":
    print(f"\nDeploying complex infrastructure via CloudFormation...")
    print(f"  Bucket: {S3_BUCKET}  |  Region: {AWS_REGION}\n")

    zip_bytes = build_zip()
    endpoints = {}

    for env, cfg in STACKS.items():
        print(f"── {env.upper()} ──────────────────────────")
        deploy_stack(cfg["stack_name"], cfg["template"])
        deploy_lambda_code(cfg["function"], zip_bytes)
        url = get_stack_output(cfg["stack_name"], cfg["output_key"])
        endpoints[env] = url
        print(f"  Endpoint: {url}\n")

    print("─" * 55)
    print("Done! Add these as GitHub Actions secrets:")
    print("  https://github.com/jossai87/awsai01/settings/secrets/actions\n")
    print(f"  BETA_API_ENDPOINT = {endpoints['beta'].replace('/synthesize', '')}")
    print(f"  PROD_API_ENDPOINT = {endpoints['prod'].replace('/synthesize', '')}")
    print(f"\nTest the endpoints:")
    for env, url in endpoints.items():
        print(f"  curl -X POST {url} -H 'Content-Type: application/json' -d '{{\"text\": \"Hello from {env}\"}}'")
