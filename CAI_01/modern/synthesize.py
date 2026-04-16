"""
synthesize.py — Live Voice Conversation with Amazon Nova 2 Sonic
----------------------------------------------------------------
Captures speech from your microphone, streams it to Nova 2 Sonic via
Bedrock's bidirectional streaming API, and plays Nova's spoken response
back through your speakers in real time. No files saved.

HOW IT WORKS:
  1. Press ENTER to start speaking
  2. Press ENTER again to stop
  3. Nova 2 Sonic listens, understands, and speaks back
  4. Repeat for a multi-turn conversation, or type 'quit' to exit

REQUIRED ENV VARS:
  AWS_ACCESS_KEY_ID     — IAM credentials
  AWS_SECRET_ACCESS_KEY — IAM credentials
  AWS_REGION            — defaults to us-east-1

REQUIRED IAM PERMISSION:
  bedrock:InvokeModelWithBidirectionalStream on amazon.nova-2-sonic-v1:0

INSTALL DEPENDENCIES:
  pip install boto3 aws-sdk-bedrock-runtime smithy-aws-core pyaudio sounddevice numpy
  brew install portaudio   (macOS)
"""

# Async runtime, base64 encoding, JSON parsing, binary struct packing, system utils, threading
import asyncio
import base64
import json
import struct
import sys
import threading
import uuid

# NumPy for audio array manipulation, sounddevice for mic/speaker I/O
import numpy as np
import sounddevice as sd

# Bedrock Runtime SDK — client and streaming input types
from aws_sdk_bedrock_runtime.client import (
    BedrockRuntimeClient,
    InvokeModelWithBidirectionalStreamOperationInput,
)
# Bedrock config — endpoint, auth scheme, and SigV4 signing
from aws_sdk_bedrock_runtime.config import (
    Config,
    HTTPAuthSchemeResolver,
    SigV4AuthScheme,
)
# Streaming input message types for the bidirectional API
from aws_sdk_bedrock_runtime.models import (
    BidirectionalInputPayloadPart,
    InvokeModelWithBidirectionalStreamInputChunk,
)
# Reads AWS credentials from environment variables
from smithy_aws_core.identity import EnvironmentCredentialsResolver
import os

# ── Audio constants ───────────────────────────────────────────────────────────
# Model ID and audio format settings for Nova 2 Sonic
MODEL_ID           = "amazon.nova-2-sonic-v1:0"
INPUT_SAMPLE_RATE  = 16000   # Hz — Nova 2 Sonic input requirement
OUTPUT_SAMPLE_RATE = 24000   # Hz — Nova 2 Sonic output rate
CHANNELS           = 1
CHUNK_FRAMES       = 1024    # frames per mic capture chunk
SAMPLE_SIZE_BITS   = 16
AWS_REGION         = os.environ.get("AWS_REGION", "us-east-1")
# ─────────────────────────────────────────────────────────────────────────────


# Build a Bedrock Runtime client configured for SigV4 auth and the correct region
def build_bedrock_client() -> BedrockRuntimeClient:
    config = Config(
        endpoint_uri=f"https://bedrock-runtime.{AWS_REGION}.amazonaws.com",
        region=AWS_REGION,
        aws_credentials_identity_resolver=EnvironmentCredentialsResolver(),
        auth_scheme_resolver=HTTPAuthSchemeResolver(),
        auth_schemes={"aws.auth#sigv4": SigV4AuthScheme(service="bedrock")},
    )
    return BedrockRuntimeClient(config=config)


# Wrap raw PCM bytes in a WAV header so audio libraries can play it
def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int) -> bytes:
    """Wrap raw PCM in a WAV header so sounddevice can play it."""
    byte_rate   = sample_rate * CHANNELS * (SAMPLE_SIZE_BITS // 8)
    block_align = CHANNELS * (SAMPLE_SIZE_BITS // 8)
    data_size   = len(pcm_bytes)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, CHANNELS,
        sample_rate, byte_rate, block_align, SAMPLE_SIZE_BITS,
        b"data", data_size,
    )
    return header + pcm_bytes


# Capture microphone audio until the user presses ENTER
def record_until_enter() -> bytes:
    """Record mic audio until the user presses ENTER. Returns raw PCM bytes."""
    frames = []
    stop_event = threading.Event()

    def callback(indata, frame_count, time_info, status):
        if not stop_event.is_set():
            frames.append(indata.copy())

    print("  🎙  Listening... (press ENTER to stop)")
    stream = sd.InputStream(
        samplerate=INPUT_SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=CHUNK_FRAMES,
        callback=callback,
    )
    with stream:
        input()  # block until ENTER
        stop_event.set()

    if not frames:
        return b""

    audio_np = np.concatenate(frames, axis=0)
    return audio_np.tobytes()


# Play raw 16-bit PCM audio through the default speaker
def play_pcm(pcm_bytes: bytes) -> None:
    """Play raw 16-bit PCM audio through the default output device."""
    if not pcm_bytes:
        return
    audio_np = np.frombuffer(pcm_bytes, dtype=np.int16)
    sd.play(audio_np, samplerate=OUTPUT_SAMPLE_RATE, blocking=True)


# Send one turn of audio to Nova 2 Sonic and collect the spoken response
async def converse_turn(client: BedrockRuntimeClient, pcm_input: bytes) -> bytes:
    """
    Send one turn of audio to Nova 2 Sonic and collect the spoken response.
    Returns raw PCM bytes of Nova's reply.
    """
    # Generate unique IDs for this conversation turn
    prompt_name        = str(uuid.uuid4())
    audio_content_name = str(uuid.uuid4())
    system_content_name = str(uuid.uuid4())

    # Open the bidirectional stream to Nova 2 Sonic
    stream = await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(model_id=MODEL_ID)
    )

    # Helper to send a JSON payload as a streaming input chunk
    async def send(payload: dict):
        chunk = InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(
                bytes_=json.dumps(payload).encode("utf-8")
            )
        )
        await stream.input_stream.send(chunk)

    # Configure the session — inference params and turn detection sensitivity
    await send({"event": {"sessionStart": {
        "inferenceConfiguration": {"maxTokens": 1024, "topP": 0.9, "temperature": 0.7},
        "turnDetectionConfiguration": {"endpointingSensitivity": "HIGH"},
    }}})

    # Start the prompt — configure text and audio output formats
    await send({"event": {"promptStart": {
        "promptName": prompt_name,
        "textOutputConfiguration": {"mediaType": "text/plain"},
        "audioOutputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": OUTPUT_SAMPLE_RATE,
            "sampleSizeBits": SAMPLE_SIZE_BITS,
            "channelCount": CHANNELS,
            "voiceId": "matthew",
            "encoding": "base64",
            "audioType": "SPEECH",
        },
    }}})

    # Send the system prompt — tells Nova its persona and behavior
    await send({"event": {"contentStart": {
        "promptName": prompt_name, "contentName": system_content_name,
        "type": "TEXT", "interactive": False, "role": "SYSTEM",
        "textInputConfiguration": {"mediaType": "text/plain"},
    }}})
    await send({"event": {"textInput": {
        "promptName": prompt_name, "contentName": system_content_name,
        "content": (
            "You are a friendly, concise voice assistant for Pixel Learning Co. "
            "Answer questions about cloud computing and AI clearly and conversationally. "
            "Keep responses short — this is a live voice conversation."
        ),
    }}})
    await send({"event": {"contentEnd": {"promptName": prompt_name, "contentName": system_content_name}}})

    # Stream the user's mic audio to Nova in base64-encoded chunks
    await send({"event": {"contentStart": {
        "promptName": prompt_name, "contentName": audio_content_name,
        "type": "AUDIO", "interactive": True, "role": "USER",
        "audioInputConfiguration": {
            "mediaType": "audio/lpcm",
            "sampleRateHertz": INPUT_SAMPLE_RATE,
            "sampleSizeBits": SAMPLE_SIZE_BITS,
            "channelCount": CHANNELS,
            "audioType": "SPEECH",
            "encoding": "base64",
        },
    }}})

    # Send audio data in chunks
    chunk_size = 1024 * 4
    for i in range(0, len(pcm_input), chunk_size):
        encoded = base64.b64encode(pcm_input[i:i + chunk_size]).decode("utf-8")
        await send({"event": {"audioInput": {
            "promptName": prompt_name,
            "contentName": audio_content_name,
            "content": encoded,
        }}})

    # Close out the prompt and session, then close the input stream
    await send({"event": {"contentEnd": {"promptName": prompt_name, "contentName": audio_content_name}}})
    await send({"event": {"promptEnd": {"promptName": prompt_name}}})
    await send({"event": {"sessionEnd": {}}})
    await stream.input_stream.close()

    # Collect Nova's spoken response — decode audio chunks from the output stream
    audio_chunks = []
    try:
        while True:
            output = await stream.await_output()
            result = await output[1].receive()
            if result.value and result.value.bytes_:
                data  = json.loads(result.value.bytes_.decode("utf-8"))
                event = data.get("event", {})
                print(f"  [debug] event keys: {list(event.keys())}")
                if "audioOutput" in event:
                    chunk = base64.b64decode(event["audioOutput"]["content"])
                    print(f"  [debug] audio chunk: {len(chunk)} bytes")
                    audio_chunks.append(chunk)
                elif "textOutput" in event:
                    text = event["textOutput"].get("content", "")
                    if text:
                        print(f"  Nova: {text}")
                elif "error" in event:
                    print(f"  [error] {event['error']}")
    except Exception as e:
        print(f"  [debug] stream ended: {e}")

    print(f"  [debug] total audio chunks: {len(audio_chunks)}, total bytes: {sum(len(c) for c in audio_chunks)}")
    return b"".join(audio_chunks)


# Main conversation loop — record, send to Nova, play response, repeat
async def main():
    print("\n🎓 Pixel Learning Co. — Live Voice Assistant (Nova 2 Sonic)")
    print("─" * 55)
    print("Press ENTER to start speaking. Type 'quit' + ENTER to exit.\n")

    client = build_bedrock_client()

    while True:
        user_input = input("Press ENTER to speak (or type 'quit' to exit): ").strip().lower()
        if user_input == "quit":
            print("Goodbye.")
            break

        pcm_input = record_until_enter()
        if not pcm_input:
            print("  No audio captured, try again.")
            continue

        print("  ⏳ Nova is thinking...")
        pcm_response = await converse_turn(client, pcm_input)

        if pcm_response:
            print("  🔊 Playing response...")
            play_pcm(pcm_response)
        else:
            print("  No audio response received. Check your mic and IAM permissions.")

        print()


if __name__ == "__main__":
    asyncio.run(main())
