# Foundational: Amazon Polly Text-to-Speech Pipeline

Converts text content into audio using Amazon Polly and uploads it to S3 via a GitHub Actions CI/CD pipeline.

```
GitHub PR    →  synthesize.py runs  →  polly-audio/beta.mp3 uploaded to S3
GitHub Merge →  synthesize.py runs  →  polly-audio/prod.mp3 uploaded to S3
```

---

## How It Works

1. `speech.txt` contains the text you want converted to audio
2. `synthesize.py` calls Amazon Polly to synthesize the text as an MP3
3. The MP3 is uploaded to your S3 bucket
4. GitHub Actions automates this on every PR (beta) and every merge (prod)

---

## Step 1 — S3 Bucket

Your bucket is already created: **`cai-01-jossai-1`** in `us-east-1`. No action needed here.

To confirm it exists:

```bash
aws s3 ls s3://cai-01-jossai-1
```

---

## Step 2 — Set Up Your Python Environment

Create a virtual environment and install boto3. You only need to do this once — the same venv works for all three projects.

```bash
python3 -m venv /tmp/cai01-venv
source /tmp/cai01-venv/bin/activate
pip install boto3
```

To confirm it worked:

```bash
python3 -c "import boto3; print(boto3.__version__)"
```

---

## Step 3 — Run the IAM Setup Script

This creates an IAM user with least-privilege permissions and prints the credentials you need for GitHub Secrets.

```bash
source /tmp/cai01-venv/bin/activate

export S3_BUCKET_NAME=cai-01-jossai-1
export AWS_REGION=us-east-1

python3 "CAI_01/foundational/scripts/setup_iam_polly.py"
```

The script will print output like this:

```
Done! Add these as GitHub Actions secrets:

  AWS_ACCESS_KEY_ID     = AKIA...
  AWS_SECRET_ACCESS_KEY = wJalr...
  AWS_REGION            = us-east-1
  S3_BUCKET_NAME        = cai-01-jossai-1
```

---

## Step 4 — Add GitHub Secrets

Go to **https://github.com/jossai87/awsai01/settings/secrets/actions** and add all four:

| Secret Name             | Value from setup script output     |
|-------------------------|------------------------------------|
| `AWS_ACCESS_KEY_ID`     | IAM user access key                |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key                |
| `AWS_REGION`            | e.g. `us-east-1`                   |
| `S3_BUCKET_NAME`        | Name of your S3 bucket             |

---

## Step 5 — Edit the Text Content (Optional)

Open `speech.txt` and replace the content with whatever you want Polly to say:

```bash
# View current content
cat "CAI_01/foundational/speech.txt"

# Edit it
nano "CAI_01/foundational/speech.txt"
```

---

## Step 6 — Trigger the Workflows

### Trigger beta (via Pull Request)

```bash
# Create a new branch and open a PR targeting main
git checkout -b test/polly-beta3
git add "CAI_01/foundational/speech.txt"
git commit -m "test: trigger beta Polly synthesis"
git push origin test/polly-beta3
```

Then open a Pull Request on GitHub targeting `main`. The `on_pull_request.yml` workflow runs automatically and uploads `polly-audio/beta.mp3`.

### Trigger prod (via Merge)

Merge the PR into `main`. The `on_merge.yml` workflow runs automatically and uploads `polly-audio/prod.mp3`.

---

## Step 7 — Verify the Uploaded Files

```bash
# List both audio files
aws s3 ls s3://cai-01-jossai-1/polly-audio/

# Download and play beta
aws s3 cp s3://cai-01-jossai-1/polly-audio/beta.mp3 ./beta.mp3

# Download and play prod
aws s3 cp s3://cai-01-jossai-1/polly-audio/prod.mp3 ./prod.mp3
```

You should see:
- `polly-audio/beta.mp3` — generated on PR
- `polly-audio/prod.mp3` — generated on merge

---

## Run Locally (Without GitHub Actions)

```bash
source /tmp/cai01-venv/bin/activate

export S3_BUCKET_NAME=cai-01-jossai-1
export AWS_REGION=us-east-1
export OUTPUT_KEY=polly-audio/local-test.mp3

python3 "CAI_01/foundational/synthesize.py"
```

---

## Troubleshooting

**AccessDenied on Polly** — The IAM user is missing `polly:SynthesizeSpeech`. Re-run `setup_iam_polly.py`.

**AccessDenied on S3** — The IAM user is missing `s3:PutObject` on your bucket. Check the bucket name matches `S3_BUCKET_NAME`.

**Workflow not triggering** — Make sure the `.github/workflows/` files are committed to the repo and GitHub Actions is enabled under repo Settings.

**Check workflow logs** — Go to your GitHub repo → **Actions** tab → click the workflow run to see detailed logs.
