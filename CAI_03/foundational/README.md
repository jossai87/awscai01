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
S3_BUCKET=your-bucket AWS_REGION=us-east-1 \
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

1. Add `.mp3` files to `CAI_03/foundational/audio_inputs/`
2. Open a PR → beta workflow runs → outputs in `s3://bucket/beta/`
3. Merge → prod workflow runs → outputs in `s3://bucket/prod/`

---

## Verify Outputs

**macOS / Linux**
```bash
aws s3 ls s3://your-bucket/beta/transcripts/
aws s3 ls s3://your-bucket/beta/translations/
aws s3 ls s3://your-bucket/beta/audio_outputs/
```

**Windows (PowerShell)**
```powershell
aws s3 ls s3://your-bucket/beta/transcripts/
aws s3 ls s3://your-bucket/beta/translations/
aws s3 ls s3://your-bucket/beta/audio_outputs/
```

---

## Supported Languages

Change `TARGET_LANG` in the workflow env to any of:

| Code | Language |
|------|----------|
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `pt` | Portuguese |
| `ja` | Japanese |
| `zh` | Chinese (Simplified) |
