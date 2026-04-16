# Modern: Amazon Nova 2 Sonic Speech-to-Speech Pipeline

> Instructor guide — written for teaching beginners. Read top to bottom before class.

---

## What This Project Does

This pipeline takes a spoken audio file, sends it to **Amazon Nova 2 Sonic** (a next-generation AI model on AWS Bedrock), and saves Nova's spoken audio response to S3.

This is **speech in → AI understands → speech out**. No text conversion. No traditional TTS engine. Nova 2 Sonic handles the full conversation natively.

```
sample_input.wav  →  Nova 2 Sonic (Bedrock)  →  nova-audio/beta.mp3  (on PR)
                                               →  nova-audio/prod.mp3  (on merge)
```

---

## How It Differs from Amazon Polly (Foundational)

| | Amazon Polly | Amazon Nova 2 Sonic |
|---|---|---|
| Input | Text | Speech (audio) |
| Output | Audio | Speech (audio) |
| Model type | Rule-based TTS engine | Foundation model (AI) |
| API style | Simple request/response | Bidirectional streaming |
| Understands context? | No | Yes |
| Conversational? | No | Yes |
| AWS service | Amazon Polly | Amazon Bedrock |

**Teaching tip:** Ask students — "What happens if the speaker in the audio has an accent, or pauses mid-sentence?" Polly can't handle that. Nova 2 Sonic can.

---

## Prerequisites

### 1. AWS Setup

You need an AWS account with the following:

**Enable Nova 2 Sonic in Bedrock:**
1. Go to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock)
2. Click "Model access" in the left sidebar
3. Find "Amazon Nova 2 Sonic" and click "Request access"
4. Wait for approval (usually instant for Nova models)

> **Gotcha #1:** Nova 2 Sonic is only available in these regions:
> `us-east-1`, `us-west-2`, `eu-north-1`, `ap-northeast-1`
> If your bucket is in another region, you still need to call Bedrock from one of these.

**Create an IAM user** with these permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModelWithBidirectionalStream"
  ],
  "Resource": "arn:aws:bedrock:*::foundation-model/amazon.nova-2-sonic-v1:0"
}
```
Plus `s3:PutObject` on your bucket.

> **Gotcha #2:** The permission is `bedrock:InvokeModelWithBidirectionalStream` — NOT
> `bedrock:InvokeModel`. Students often copy Polly IAM policies and wonder why it fails.

### 2. GitHub Secrets

Go to your repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret Name | Example Value | Notes |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | From IAM user |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | From IAM user |
| `AWS_REGION` | `us-east-1` | Must be a supported Nova 2 Sonic region |
| `S3_BUCKET_NAME` | `my-audio-bucket` | Must already exist |

### 3. The Input Audio File

Commit a file called `sample_input.wav` to the `modern/` folder. This is the audio Nova 2 Sonic will listen to and respond to.

**Requirements for the WAV file:**
- Any format works — ffmpeg will auto-convert it
- Keep it under 5 minutes (8-minute session limit on Nova 2 Sonic)
- Speak clearly — Nova 2 Sonic is robust to noise but clear audio = better responses

**Quick way to create one (macOS):**
```bash
# Record 10 seconds from your mic
sox -d -r 16000 -c 1 -b 16 modern/sample_input.wav trim 0 10
```

**Or convert an existing MP3:**
```bash
ffmpeg -i my_audio.mp3 -ar 16000 -ac 1 -sample_fmt s16 modern/sample_input.wav
```

> **Gotcha #3:** Nova 2 Sonic expects 16kHz, 16-bit, mono PCM audio. The script handles
> this conversion automatically via ffmpeg, but ffmpeg must be installed. The GitHub
> Actions workflow installs it automatically.

---

## Running Locally (for testing before pushing)

```bash
# Install dependencies
pip install -r modern/requirements.txt

# Install ffmpeg (macOS)
brew install ffmpeg

# Set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1
export S3_BUCKET_NAME=your-bucket-name
export INPUT_AUDIO_FILE=modern/sample_input.wav
export OUTPUT_KEY=nova-audio/test.mp3

# Run
python3 modern/synthesize.py
```

---

## Triggering the Workflows

**Beta (PR workflow):**
1. Create a new branch: `git checkout -b update-audio`
2. Swap out `sample_input.wav` with new audio
3. Push and open a Pull Request to `main`
4. GitHub Actions runs → `nova-audio/beta.mp3` appears in S3

**Prod (merge workflow):**
1. Review the beta audio in S3
2. Approve and merge the PR
3. GitHub Actions runs → `nova-audio/prod.mp3` appears in S3

---

## Verifying the Output

```bash
# List uploaded files
aws s3 ls s3://your-bucket-name/nova-audio/

# Download and listen
aws s3 cp s3://your-bucket-name/nova-audio/beta.mp3 ./beta.mp3
open beta.mp3   # macOS
```

---

## Gotchas — Instructor Cheat Sheet

| # | Gotcha | Fix |
|---|---|---|
| 1 | Wrong region | Nova 2 Sonic only works in `us-east-1`, `us-west-2`, `eu-north-1`, `ap-northeast-1` |
| 2 | Wrong IAM permission | Use `bedrock:InvokeModelWithBidirectionalStream`, not `bedrock:InvokeModel` |
| 3 | Model access not enabled | Enable Nova 2 Sonic in Bedrock Console → Model access |
| 4 | Empty audio response | Usually means the input audio was silence or too short — check your WAV file |
| 5 | `aws-sdk-bedrock-runtime` not found | This is the smithy SDK, not standard boto3. Run `pip install aws-sdk-bedrock-runtime` |
| 6 | ffmpeg not found | Install with `brew install ffmpeg` (Mac) or `apt-get install ffmpeg` (Linux) |
| 7 | 8-minute session limit | Nova 2 Sonic cuts off at 8 minutes. Split long audio into segments if needed |
| 8 | `sample_input.wav` missing | The file must be committed to the repo — it's the audio input for the pipeline |

---

## How the Code Works (for class walkthrough)

Open `synthesize.py` and walk through these sections with students:

1. **`convert_to_pcm_wav()`** — ffmpeg converts any audio to the format Nova needs
2. **`speech_to_speech()`** — the main async function; explain bidirectional streaming
   - `sessionStart` → opens the "phone call"
   - `promptStart` → configures the voice and output format
   - `contentStart` (SYSTEM) → gives Nova its instructions
   - `audioInput` loop → streams audio chunks like a real microphone
   - `contentEnd / promptEnd / sessionEnd` → hangs up
   - response loop → collects Nova's spoken reply
3. **`pcm_to_mp3()`** — converts Nova's raw PCM output to a playable MP3
4. **`main()`** — ties it all together and uploads to S3

**Discussion question for class:**
> "Why do we send audio in small chunks instead of one big file?"
> Answer: Because Nova 2 Sonic is designed for real-time streaming. Chunking simulates
> a live microphone and allows the model to start processing before the audio ends.

---

## Architecture Diagram

```
GitHub Repo
  └── sample_input.wav  (your spoken audio)
  └── synthesize.py

GitHub Actions (on PR or merge)
  │
  ├── ffmpeg: convert input audio → 16kHz PCM WAV
  │
  ├── Bedrock bidirectional stream → amazon.nova-2-sonic-v1:0
  │     ├── Send: sessionStart, promptStart, system prompt
  │     ├── Send: audio chunks (base64 PCM)
  │     └── Receive: audio chunks (base64 PCM) ← Nova's spoken response
  │
  ├── ffmpeg: PCM → MP3
  │
  └── S3: nova-audio/beta.mp3  or  nova-audio/prod.mp3
```
