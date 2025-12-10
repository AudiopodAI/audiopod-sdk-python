# AudioPod Python SDK

Official Python SDK for [AudioPod AI](https://audiopod.ai) - Professional Audio Processing powered by AI.

## Installation

```bash
pip install audiopod
```

## Quick Start

```python
from audiopod import Client

# Initialize client
client = Client(api_key="ap_your_api_key")
# Or set AUDIOPOD_API_KEY environment variable

# Check wallet balance
balance = client.wallet.get_balance()
print(f"Balance: {balance['balance_usd']}")

# Extract stems from audio
job = client.stem_extraction.extract_stems(
    audio_file="song.mp3",
    stem_types=["vocals", "drums", "bass", "other"],
    wait_for_completion=True
)

# Download stems
for stem, url in job["download_urls"].items():
    print(f"{stem}: {url}")
```

## Services

### Wallet (API Billing)

```python
# Get balance
balance = client.wallet.get_balance()

# Get pricing
pricing = client.wallet.get_pricing()

# Estimate cost
estimate = client.wallet.estimate_cost("stem_extraction", duration_seconds=300)

# Top up wallet
checkout = client.wallet.create_topup_checkout(amount_cents=2500)  # $25
print(f"Pay at: {checkout['url']}")

# Usage history
usage = client.wallet.get_usage_history(page=1, limit=50)
```

### Stem Extraction

```python
# Extract all stems
job = client.stem_extraction.extract_stems(
    audio_file="song.mp3",
    stem_types=["vocals", "drums", "bass", "other"],
    wait_for_completion=True
)

# From URL
job = client.stem_extraction.extract_stems(
    url="https://example.com/song.mp3",
    stem_types=["vocals", "other"]
)

# Check status
status = client.stem_extraction.get_job(job_id=123)
```

### Transcription

```python
# Transcribe audio
result = client.transcription.transcribe(
    audio_file="podcast.mp3",
    speaker_diarization=True,
    wait_for_completion=True
)
print(result["transcript"])
```

### Voice Cloning & TTS

```python
# List voices
voices = client.voice.list_voices()

# Generate speech
audio = client.voice.generate_speech(
    text="Hello, world!",
    voice_id=123,
    wait_for_completion=True
)
```

### Music Generation

```python
# Generate music
result = client.music.generate(
    prompt="upbeat electronic dance music",
    duration=30,
    wait_for_completion=True
)
```

### Noise Reduction

```python
# Denoise audio
result = client.denoiser.denoise(
    audio_file="noisy.mp3",
    mode="studio",
    wait_for_completion=True
)
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
    APIError
)

try:
    client = Client()
    job = client.stem_extraction.extract_stems(audio_file="song.mp3")
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
- [API Wallet](https://docs.audiopod.ai/account/api-wallet)
- [Stem Separation](https://docs.audiopod.ai/api-reference/stem-splitter)

## License

MIT

