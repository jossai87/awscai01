# Foundational: Multilingual Audio Pipeline

Transcribes English .mp3 files, translates the text, and synthesizes speech in the target language — all via GitHub Actions.

```
audio_inputs/*.mp3
  → S3 upload
  → Amazon Transcribe  → transcript text
  → Amazon Translate   → translated text
  → Amazon Polly       → translated audio
  → S3 structured outputs:
      {env}/transcripts/{stem}.txt
      {env}/translations/{stem}_{lang}.txt
      {env}/audio_outputs/{stem}_{lang}.mp3
```

---

## AWS Resources Required

- S3 bucket (any existing bucket)
- IAM user with: `s3:PutObject`, `s3:GetObject`, `transcribe:StartTranscriptionJob`, `transcribe:GetTranscriptionJob`, `translate:TranslateText`, `polly:SynthesizeSpeech`

Run the setup script to provision automatically:

**macOS / Linux**
```bash
source venv/bin/activate
S3_BUCKET=cai-01-jossai-1 \
AWS_REGION=us-east-1 \
python3 CAI_03/foundational/scripts/setup_foundational.py
```

**Windows (PowerShell)**
```powershell
$env:S3_BUCKET = "your-bucket"
$env:AWS_REGION = "us-east-1"
python CAI_03/foundational/scripts/setup_foundational.py
```

---

## GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET` | Your bucket name |

---

## Adding Audio Files

1. Add an English `.mp3` file to `CAI_03/foundational/audio_inputs/` — the pipeline requires at least one or it will fail. Any English speech recording works.
2. Create a new branch and open a PR:

```bash
git checkout -b feature/test-audio-pipeline
git add CAI_03/foundational/audio_inputs/
git commit -m "add audio file for transcription pipeline"
git push -u origin feature/test-audio-pipeline
```

3. Open a pull request from `feature/test-audio-pipeline` → `main` on GitHub
4. Beta workflow runs automatically → outputs in `s3://cai-01-jossai-1/beta/`
5. Merge → prod workflow runs → outputs in `s3://cai-01-jossai-1/prod/`

---

## Verify Outputs

**macOS / Linux**
```bash
aws s3 ls s3://cai-01-jossai-1/beta/transcripts/
aws s3 ls s3://cai-01-jossai-1/beta/translations/
aws s3 ls s3://cai-01-jossai-1/beta/audio_outputs/
```

**Windows (PowerShell)**
```powershell
aws s3 ls s3://cai-01-jossai-1/beta/transcripts/
aws s3 ls s3://cai-01-jossai-1/beta/translations/
aws s3 ls s3://cai-01-jossai-1/beta/audio_outputs/
```

---

## Supported Languages

The pipeline defaults to Spanish (`es`). To change the language, update `TARGET_LANG` in both workflow files:

- `.github/workflows/cai03_foundational_pr.yml` (beta)
- `.github/workflows/cai03_foundational_merge.yml` (prod)

Find this line in each file and change the value:

```yaml
TARGET_LANG: es
```

Supported codes:

| Code | Language |
|------|----------|
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `pt` | Portuguese |
| `ja` | Japanese |
| `zh` | Chinese (Simplified) |

You can also override it locally when running the script directly:

```bash
S3_BUCKET=cai-01-jossai-1 \
DYNAMODB_TABLE=beta_results \
BRANCH=feature/test-audio-pipeline \
TARGET_LANG=fr \
python3 CAI_03/foundational/process_audio.py
```
