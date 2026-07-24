# AudioPod Python SDK

Official Python SDK for [AudioPod AI](https://audiopod.ai) — an all-in-one AI
**audio** platform: music generation, text-to-speech (with directing), voice
cloning, stem separation, transcription, speaker separation, noise reduction,
translation, and audiobook production.

This SDK is the **Platform (API + Agent)** surface of AudioPod — the developer
entry point alongside the [Node.js SDK](https://www.npmjs.com/package/audiopod),
the CLI, and the MCP server. **Start free** — mint a key, get free credits to
try, no card required. API usage is **pay-as-you-go** ($1 = 7,500 credits,
credits never expire). Get a key at
[audiopod.ai/dashboard/account/api-keys](https://www.audiopod.ai/dashboard/account/api-keys).

## Installation

```bash
pip install audiopod
```

## Quick Start

```python
from audiopod import Client

# Reads AUDIOPOD_API_KEY, or pass api_key="ap_your_api_key"
client = Client()

# Text-to-speech
job = client.voice.generate_speech(
    voice_id=368,
    text="Welcome to AudioPod.",
    wait_for_completion=True,
)
print(job["output_url"])
```

## Text-to-Speech

500+ voices across 85+ languages, with **inline directing** written straight
into the text.

```python
# Emotion, non-verbal sounds, pauses, and pronunciation — all inline in `text`
job = client.voice.generate_speech(
    voice_id=368,
    text='[warm, unhurried] Good evening. [breathe] Tonight, a story. '
         '<break time="600ms"/> It begins in Worcester /ˈwʊstər/.',
    wait_for_completion=True,
)
```

- **Emotion / delivery** — a leading bracket per segment: `[whispering, tense] …`
- **Non-verbal sounds** — `[laugh] [sigh] [clear throat] [breathe] [cough] [yawn] [chuckle] [gasp] [groan]`
- **Pauses** — `<break time="500ms"/>` (≤10s each, ≤20 per request)
- **Pronunciation** — inline IPA between slashes: `Worcester /ˈwʊstər/`

Word-level timestamps (for follow-along / karaoke UIs) and **Voice Design**
(create a voice from a text description) are available via the REST API — see
[the docs](https://docs.audiopod.ai/api-reference/text-to-speech).

## Voice Cloning

```python
# Instant clone from a 5–30s reference clip
voice = client.voice.create_voice(name="My Voice", audio_file="sample.wav")

# Reuse the clone for TTS
job = client.voice.generate_speech(
    voice_id=voice["id"], text="Now in my own voice.", wait_for_completion=True
)
```

Voice conversion (voice-to-voice) is available via the REST API — see
[Voice Changer](https://docs.audiopod.ai/api-reference/voice-changer).

## Music Generation

```python
# Duration is not tier-capped (10s–10min)
result = client.music.generate(
    prompt="upbeat synthwave, 120 BPM, driving bassline",
    duration=60,
    wait_for_completion=True,
)
```

## Stem Separation

```python
# Extract stems (vocals, drums, bass, other)
job = client.stem_extraction.extract_stems(
    audio_file="song.mp3",
    stem_types=["vocals", "drums", "bass", "other"],
    wait_for_completion=True,
)
for stem, url in job["download_urls"].items():
    print(f"{stem}: {url}")
```

## Audio to MIDI

Convert a mix — or stems you already separated — into MIDI (bass, vocals,
piano by default; guitar is opt-in/experimental). It's a starting-point
transcription: tidy timing/lengths in your DAW, drums aren't transcribed
yet, and dynamics are approximate.

```python
# Standalone: split + transcribe in one call (default stems: bass, vocals, piano)
job = client.midi.convert(file="song.mp3")
print(job["merged_midi_url"])

# Add-on: transcribe stems you already separated (bills the add-on rate only)
job = client.midi.convert_from_stem_job(stem_job_id=job["id"])
for stem, url in (job["midi_urls"] or {}).items():
    print(f"{stem}: {url}")
```

## Transcription

```python
# Speaker labels + word timestamps
result = client.transcription.transcribe(
    audio_file="podcast.mp3",
    speaker_diarization=True,
    wait_for_completion=True,
)
print(result["transcript"])
```

Premium-accuracy transcription and real-time streaming are also supported —
see [Speech-to-Text](https://docs.audiopod.ai/api-reference/speech-to-text).

## Other Audio Services

```python
# Speaker separation / diarization
speakers = client.speaker.diarize(audio_file="interview.wav", wait_for_completion=True)

# Noise reduction
clean = client.denoiser.denoise(audio_file="noisy.mp3", mode="studio", wait_for_completion=True)

# Translate / dub speech into another language
dubbed = client.translation.translate(audio_file="clip.mp3", target_language="es")

# Audiobook production (manuscript → ACX-ready export)
project = client.audiobook.create_project(title="My Book", author="Jane Doe")
```

## OpenAI-Compatible Endpoints

Already have OpenAI-shaped audio code? Point it at AudioPod — set the client
base URL to `https://api.audiopod.ai/api/v1` and `Authorization: Bearer ap_...`.
The `/audio/speech`, `/audio/transcriptions`, and `/audio/translations`
endpoints behave like their OpenAI counterparts. See
[OpenAI compatibility](https://docs.audiopod.ai/api-reference/openai-compatibility).

## API Wallet

```python
# Balance and cost estimate
balance = client.wallet.get_balance()
estimate = client.wallet.estimate_cost("text_to_speech", duration_seconds=180)

# Top up
checkout = client.wallet.create_topup_checkout(amount_cents=2500)  # $25
print(f"Pay at: {checkout['url']}")
```

## Async Support

```python
import asyncio
from audiopod import AsyncClient

async def main():
    async with AsyncClient() as client:
        balance = await client.wallet.get_balance()
        print(f"Balance: {balance['balance_usd']}")

asyncio.run(main())
```

## Error Handling

```python
from audiopod import Client
from audiopod.exceptions import (
    AuthenticationError,
    InsufficientBalanceError,
    RateLimitError,
    APIError,
)

try:
    client = Client()
    job = client.voice.generate_speech(voice_id=368, text="Hello")
except AuthenticationError:
    print("Invalid API key")
except InsufficientBalanceError as e:
    print(f"Need to top up: required {e.required_cents} cents")
except RateLimitError:
    print("Rate limit exceeded, try again later")
except APIError as e:
    print(f"API error ({e.status_code}): {e}")
```

## Documentation

- [API Reference](https://docs.audiopod.ai)
- [Text-to-Speech](https://docs.audiopod.ai/api-reference/text-to-speech)
- [API Wallet](https://docs.audiopod.ai/account/api-wallet)

## License

MIT
