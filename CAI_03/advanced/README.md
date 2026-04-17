# Advanced: Event-Driven Multilingual Audio Pipeline (Lambda + S3 Trigger)

GitHub Actions uploads .mp3 files to S3. An S3 event notification triggers a Lambda that runs the full Transcribe → Translate → Polly pipeline automatically.

```
GitHub Actions
  → s3 cp audio_inputs/*.mp3 (with metadata env=beta|prod)
       ↓ S3 trigger (audio_inputs/*.mp3)
   Lambda (multilingual-audio-handler)
       ↓
   Transcribe → Translate → Polly
       ↓
   S3 outputs: {env}/transcripts/, translations/, audio_outputs/
```

---

## AWS Resources Required

Run the setup script — it provisions everything:

**macOS / Linux**
```bash
S3_BUCKET=your-bucket AWS_REGION=us-east-1 \
  python3 CAI_03/advanced/scripts/setup_advanced.py
```

**Windows (PowerShell)**
```powershell
$env:S3_BUCKET = "your-bucket"
$env:AWS_REGION = "us-east-1"
python CAI_03/advanced/scripts/setup_advanced.py
```

Creates: Lambda execution role, `multilingual-audio-handler` Lambda, S3 event notification, CI IAM user.

---

## GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | CI IAM access key |
| `AWS_SECRET_ACCESS_KEY` | CI IAM secret key |
| `AWS_REGION` | e.g. `us-east-1` |
| `S3_BUCKET` | Your bucket name |

---

## How Environment Is Determined

The Lambda reads the `env` metadata tag set by the GitHub Actions upload step:
- Feature branch push → `env=beta`
- Merge to main → `env=prod`

Fallback: if metadata is missing, filename prefix is used (`beta-*.mp3` → beta).
