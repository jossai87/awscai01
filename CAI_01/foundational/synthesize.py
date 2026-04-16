# synthesize.py — reads speech.txt, converts it to audio via Polly, uploads MP3 to S3
#
# Required env vars: S3_BUCKET_NAME, AWS_REGION (default: us-east-1)
# Optional env var:  OUTPUT_KEY (default: polly-audio/output.mp3)

import boto3
import os


def synthesize_and_upload(output_key: str) -> None:
    # Resolve speech.txt relative to this file's location
    text_file = os.path.join(os.path.dirname(__file__), "speech.txt")
    bucket = os.environ["S3_BUCKET_NAME"]

    with open(text_file, "r") as f:
        text = f.read()

    # Create a Polly client and synthesize the text as an MP3
    polly = boto3.client("polly", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Joanna",
        Engine="neural",  # neural = more natural-sounding than "standard"
    )

    # Read the audio bytes from Polly's streaming response
    audio_stream = response["AudioStream"].read()

    # Upload directly to S3 — no need to save a local file first
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=audio_stream,
        ContentType="audio/mpeg",
    )

    print(f"Uploaded audio to s3://{bucket}/{output_key}")


if __name__ == "__main__":
    # GitHub Actions sets OUTPUT_KEY to beta.mp3 or prod.mp3 depending on the workflow
    output_key = os.environ.get("OUTPUT_KEY", "polly-audio/output.mp3")
    synthesize_and_upload(output_key)
