"""
handler.py — Event-Driven Multilingual Audio Lambda
----------------------------------------------------
Triggered by S3 uploads to audio_inputs/*.mp3.
Reads env from object metadata ({"env": "beta"} or {"env": "prod"}).
Falls back to filename prefix: beta-*.mp3 → beta, prod-*.mp3 → prod.

Performs the full pipeline:
  Transcribe → Translate → Polly → S3 outputs

Required Lambda environment variables:
  TARGET_LANG  — language code (default: es)
  AWS_REGION   — AWS region
"""

import boto3
import json
import os
import time
import urllib.parse
import uuid

TARGET_LANG = os.environ.get("TARGET_LANG", "es")
AWS_REGION  = os.environ.get("AWS_REGION",  "us-east-1")

s3         = boto3.client("s3",         region_name=AWS_REGION)
transcribe = boto3.client("transcribe", region_name=AWS_REGION)
translate  = boto3.client("translate",  region_name=AWS_REGION)
polly      = boto3.client("polly",      region_name=AWS_REGION)

VOICE_MAP = {
    "es": ("Lucia",  "neural"),
    "fr": ("Lea",    "neural"),
    "de": ("Vicki",  "neural"),
    "pt": ("Ines",   "neural"),
    "ja": ("Kazuha", "neural"),
    "zh": ("Zhiyu",  "standard"),
}


def get_env(bucket: str, key: str, filename: str) -> str:
    """Determine environment from object metadata or filename prefix."""
    try:
        meta = s3.head_object(Bucket=bucket, Key=key).get("Metadata", {})
        if meta.get("env") in ("beta", "prod"):
            return meta["env"]
    except Exception:
        pass
    return "prod" if filename.startswith("prod-") else "beta"


def transcribe_audio(bucket: str, key: str, job_name: str) -> str:
    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": f"s3://{bucket}/{key}"},
        MediaFormat="mp3",
        LanguageCode="en-US",
        OutputBucketName=bucket,
        OutputKey=f"_transcribe_tmp/{job_name}.json",
    )
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        state  = status["TranscriptionJob"]["TranscriptionJobStatus"]
        if state == "COMPLETED":
            break
        if state == "FAILED":
            raise RuntimeError(f"Transcription failed: {status['TranscriptionJob'].get('FailureReason')}")
        time.sleep(5)

    obj  = s3.get_object(Bucket=bucket, Key=f"_transcribe_tmp/{job_name}.json")
    data = json.loads(obj["Body"].read())
    return data["results"]["transcripts"][0]["transcript"]


def translate_text(text: str) -> str:
    return translate.translate_text(
        Text=text,
        SourceLanguageCode="en",
        TargetLanguageCode=TARGET_LANG,
    )["TranslatedText"]


def synthesize_speech(text: str) -> bytes:
    voice_id, engine = VOICE_MAP.get(TARGET_LANG, ("Joanna", "neural"))
    return polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=voice_id,
        Engine=engine,
    )["AudioStream"].read()


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket   = record["s3"]["bucket"]["name"]
        key      = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        filename = key.split("/")[-1]
        stem     = filename.rsplit(".", 1)[0]
        env      = get_env(bucket, key, filename)
        job_name = f"cai03-{stem}-{uuid.uuid4().hex[:8]}"

        print(f"[{env}] Processing s3://{bucket}/{key}")

        transcript  = transcribe_audio(bucket, key, job_name)
        translation = translate_text(transcript)
        audio_bytes = synthesize_speech(translation)

        outputs = {
            f"{env}/transcripts/{stem}.txt":              (transcript.encode(),  "text/plain"),
            f"{env}/translations/{stem}_{TARGET_LANG}.txt": (translation.encode(), "text/plain"),
            f"{env}/audio_outputs/{stem}_{TARGET_LANG}.mp3": (audio_bytes,         "audio/mpeg"),
        }
        for out_key, (body, content_type) in outputs.items():
            s3.put_object(Bucket=bucket, Key=out_key, Body=body, ContentType=content_type)
            print(f"  Uploaded: s3://{bucket}/{out_key}")

    return {"statusCode": 200, "body": "OK"}
