# Stores Terraform state remotely in S3 so it's shared across the team.
# Use a separate bucket from your app bucket — don't mix state and data.
# Run `terraform init` after updating this to connect to the backend.

terraform {
  backend "s3" {
    bucket = "cai-01-jossai-1-tfstate"
    key    = "polly-pipeline/terraform.tfstate"
    region = "us-east-1"
  }
}
