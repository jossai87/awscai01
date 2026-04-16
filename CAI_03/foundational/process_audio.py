"""
process_audio.py — Multilingual Audio Pipeline
-----------------------------------------------
For each .mp3 in audio_inputs/:
  1. Uploads the .mp3 to S3 under audio_inputs/{filename}
  2. Transcribes it using Amazon Transcribe
  3. Translates the transcript using Amazon Translate
  4. Synthesizes translated text into speech using Amazon Polly
  5. Uploads all three outputs to structured S3 paths:
       {ENV}/transcripts/{stem}.txt
       {ENV}/translations/{stem}_{lang}.txt
       {ENV}/audio_outputs/{stem}_{lang}.mp3

REQUIRED ENV VARS:
  S3_BUCKET     — S3 bucket name
  ENV           — beta or prod (controls S3 prefix)
  TARGET_LANG   — language code to translate into (default: es)
  AWS_REGION    — defaults to us-east-1

SUPPORTED TARGET_LANG CODES (examples):
  es = Spanish   fr = French    de = German
  pt = Portuguese  ja = Japanese  zh = Chinese (Simplified)
"""

import boto3
import json
import os
import time
import uuid
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
S3_BUCKET   = os.environ["S3_BUCKET"]
ENV         = os.environ.get("ENV", "beta")
TARGET_LANG = os.environ.get("TARGET_LANG", "es")
AWS_REGION  = os.environ.get("AWS_REGION", "us-east-1")
AUDIO_DIR   = Path(__file__).parent / "audio_inputs"

# Polly voice per language (neural where available)
VOICE_MAP = {
    "es": ("Lucia",   "neural"),
    "fr": ("Lea",     "neural"),
    "de": ("Vicki",   "neural"),
    "pt": ("Ines",    "neural"),
    "ja": ("Kazuha",  "neural"),
    "zh": ("Zhiyu",   "standard"),
}
# ─────────────────────────────────────────────────────────────────────────────

s3          = boto3.client("s3",          region_name=AWS_REGION)
transcribe  = boto3.client("transcribe",  region_name=AWS_REGION)
translate   = boto3.client("translate",   region_name=AWS_REGION)
polly       = boto3.client("polly",       region_name=AWS_REGION)


def upload_input(local_path: Path) -> str:
    """Upload source .mp3 to S3 and return the key."""
    key = f"audio_inputs/{local_path.name}"
    s3.upload_file(str(local_path), S3_BUCKET, key, ExtraArgs={"ContentType": "audio/mpeg"})
    print(f"  Uploaded input: s3://{S3_BUCKET}/{key}")
    return key


def transcribe_audio(s3_key: str, job_name: str) -> str:
    """Start a Transcribe job and wait for completion. Returns transcript text."""
    s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="mp3",
        LanguageCode="en-US",
        OutputBucketName=S3_BUCKET,
        OutputKey=f"_transcribe_tmp/{job_name}.json",
    )

    print(f"  Transcribing... (job: {job_name})")
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        state  = status["TranscriptionJob"]["TranscriptionJobStatus"]
        if state == "COMPLETED":
            break
        if state == "FAILED":
            raise RuntimeError(f"Transcription failed: {status['TranscriptionJob'].get('FailureReason')}")
        time.sleep(5)

    # Fetch the transcript JSON from S3
    result_key = f"_transcribe_tmp/{job_name}.json"
    obj  = s3.get_object(Bucket=S3_BUCKET, Key=result_key)
    data = json.loads(obj["Body"].read())
    text = data["results"]["transcripts"][0]["transcript"]
    print(f"  Transcript: {text[:80]}{'...' if len(text) > 80 else ''}")
    return text


def translate_text(text: str) -> str:
    """Translate English text to TARGET_LANG."""
    response = translate.translate_text(
        Text=text,
        SourceLanguageCode="en",
        TargetLanguageCode=TARGET_LANG,
    )
    translated = response["TranslatedText"]
    print(f"  Translation ({TARGET_LANG}): {translated[:80]}{'...' if len(translated) > 80 else ''}")
    return translated


def synthesize_speech(text: str) -> bytes:
    """Synthesize translated text to MP3 using Polly."""
    voice_id, engine = VOICE_MAP.get(TARGET_LANG, ("Joanna", "neural"))
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=voice_id,
        Engine=engine,
        LanguageCode=TARGET_LANG if TARGET_LANG != "es" else "es-ES",
    )
    return response["AudioStream"].read()


def upload_outputs(stem: str, transcript: str, translation: str, audio: bytes) -> dict:
    """Upload all three outputs to structured S3 paths. Returns dict of keys."""
    keys = {
        "transcript":  f"{ENV}/transcripts/{stem}.txt",
        "translation": f"{ENV}/translations/{stem}_{TARGET_LANG}.txt",
        "audio":       f"{ENV}/audio_outputs/{stem}_{TARGET_LANG}.mp3",
    }
    s3.put_object(Bucket=S3_BUCKET, Key=keys["transcript"],  Body=transcript.encode(),  ContentType="text/plain")
    s3.put_object(Bucket=S3_BUCKET, Key=keys["translation"], Body=translation.encode(), ContentType="text/plain")
    s3.put_object(Bucket=S3_BUCKET, Key=keys["audio"],       Body=audio,                ContentType="audio/mpeg")

    for label, key in keys.items():
        print(f"  Uploaded {label}: s3://{S3_BUCKET}/{key}")
    return keys


def process(audio_path: Path) -> None:
    stem     = audio_path.stem
    job_name = f"cai03-{stem}-{uuid.uuid4().hex[:8]}"

    print(f"\nProcessing: {audio_path.name}")
    s3_key     = upload_input(audio_path)
    transcript = transcribe_audio(s3_key, job_name)
    translation = translate_text(transcript)
    audio_bytes = synthesize_speech(translation)
    upload_outputs(stem, transcript, translation, audio_bytes)


if __name__ == "__main__":
    files = list(AUDIO_DIR.glob("*.mp3"))
    if not files:
        print(f"No .mp3 files found in {AUDIO_DIR}. Add audio files to audio_inputs/.")
        raise SystemExit(1)

    print(f"Found {len(files)} file(s). ENV={ENV} | TARGET_LANG={TARGET_LANG} | Bucket={S3_BUCKET}")
    for f in files:
        process(f)
    print("\nDone.")
