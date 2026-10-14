# AudioPod Python SDK

Add **speech-to-text with speaker labels, text-to-speech, voice cloning, stem
separation / vocal removal, audio-to-MIDI, music generation and noise
reduction** to a Python app with one package and one API key.

```bash
pip install audiopod
export AUDIOPOD_API_KEY=ap_...   # https://audiopod.ai/dashboard/account/api-keys
```

```python
from audiopod import Client
job = Client().transcription.transcribe(url="https://example.com/talk.mp3", speaker_diarization=True, wait_for_completion=True)
print(job["id"], job["status"])
```

| Job | Method | Guide |
|---|---|---|
| Speech to text, speaker diarization, subtitles | `client.transcription.transcribe(...)` | [transcription](https://docs.audiopod.ai/quickstarts/transcription) |
| Text to speech (500+ voices, inline directing) | `client.voice.generate_speech(...)` | [text-to-speech](https://docs.audiopod.ai/quickstarts/text-to-speech) |
| Voice cloning | `client.voice.create_voice(..., wait_for_ready=True)` | [voice cloning](https://docs.audiopod.ai/quickstarts/voice-cloning) |
| Stem separation, vocal remover, karaoke | `client.stem_extraction.separate(...)` | [stems](https://docs.audiopod.ai/quickstarts/stem-separation) |
| Audio to MIDI | `client.midi.convert(...)` | [MIDI](https://docs.audiopod.ai/quickstarts/audio-to-midi) |
| Music generation | `client.music.generate(...)` | [music](https://docs.audiopod.ai/quickstarts/music) |
| Noise reduction | `client.denoiser.denoise(...)` | [noise reduction](https://docs.audiopod.ai/quickstarts/noise-reduction) |
| Speaker separation | `client.speaker.diarize(...)` | [speakers](https://docs.audiopod.ai/api-reference/speaker-separation) |

**Billing:** API-key requests are paid from a prepaid USD **API wallet** first
and, when it can't cover a job, from your account's plan or pay-as-you-go
credits. Your first API key comes with a $1 starter credit in the wallet
(verified email). See wallet rates with `client.wallet.get_pricing()`; top up
the wallet from the [API keys page](https://audiopod.ai/dashboard/account/api-keys)
or add credits at [audiopod.ai/pricing](https://audiopod.ai/pricing). Coding agents:
read [AGENTS.md](AGENTS.md).

This SDK is the **Platform (API + Agent)** surface of AudioPod, alongside the
[Node.js SDK](https://www.npmjs.com/package/audiopod), the `audiopod` CLI, and
the MCP server.

[![Run in Postman](https://run.pstmn.io/button.svg)](https://god.gw.postman.com/run-collection/58401244-916ddbda-1a70-4c07-8ccd-fe524703a84b?action=collection%2Ffork&source=rip_markdown&collection-url=entityId%3D58401244-916ddbda-1a70-4c07-8ccd-fe524703a84b%26entityType%3Dcollection%26workspaceId%3D8013472d-5897-47d1-bf5c-92683a027b35&utm_source=audiopod-sdk-python)

Want to see a response before installing anything? The **Getting Started**
collection reaches a real `200` in two requests with no account and no API key.
[More about the collections](https://docs.audiopod.ai/sdks/postman).

## Quick start: one call per task

Set `AUDIOPOD_API_KEY` (or pass `api_key="ap_..."`), then each task is one
call that waits for the job and returns its output links.

**Transcribe with speaker labels**

```python
from audiopod import Client
client = Client()
job = client.transcription.transcribe(url="https://example.com/interview.mp3", speaker_diarization=True, wait_for_completion=True)
for seg in client.transcription.get_transcript(job["id"])["segments"]:
    print(seg.get("speaker_label"), seg["text"])
```

**Split a song into stems**

```python
from audiopod import Client
client = Client()
job = client.stem_extraction.separate(file="song.mp3", mode="four")  # vocals, drums, bass, other
for stem, link in job["download_urls"].items():
    print(stem, link)
```

**Text to speech**

```python
from audiopod import Client
client = Client()
job = client.voice.generate_speech(voice_id=368, text="Welcome to AudioPod.", wait_for_completion=True)
print(job["output_url"])
```

**Generate music**

```python
from audiopod import Client
client = Client()
track = client.music.generate(prompt="lo-fi hip hop, 80 BPM, soft piano", duration=60, wait_for_completion=True)
print(track["output_url"])
```

**Audio to MIDI / noise removal**

```python
from audiopod import Client
client = Client()
print(client.midi.convert(file="song.mp3")["merged_midi_url"])
print(client.denoiser.denoise(file="voice-memo.m4a")["output_url"])
```

Step-by-step guides for each task start at
[docs.audiopod.ai/quickstarts/transcription](https://docs.audiopod.ai/quickstarts/transcription).

## Using with AI agents

- **Coding agents (Claude Code, Cursor, Copilot, Windsurf):** tell the agent to
  use the `audiopod` package and point it at
  [docs.audiopod.ai/llms.txt](https://docs.audiopod.ai/llms.txt). Every docs page
  is also served as Markdown: add `.md` to its URL.
- **Agents as tools (MCP):** connect `https://mcp.audiopod.ai/core` (transcribe,
  stems, cleanup, MIDI) or `https://mcp.audiopod.ai` (adds speech, voices and
  music). Sign-in is OAuth; an `X-API-Key` header works for CI.
- **Claude Code plugin:** `/plugin marketplace add AudiopodAI/claude-plugin`, then
  `/plugin install audiopod@audiopod`.
- **ChatGPT:** add `https://mcp.audiopod.ai/core` as a connector in developer mode.

Setup for every client, plus copy-paste prompts:
[AudioPod for AI agents](https://docs.audiopod.ai/agents).

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
# Instant clone from a 5–30s reference clip. A new clone is PENDING while it
# processes; wait_for_ready=True returns once it is COMPLETED and usable.
voice = client.voice.create_voice(name="My Voice", audio_file="sample.wav", wait_for_ready=True)

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

Every plan now gets the highest-quality music model at the standard rate, so
the old `quality=` argument is no longer needed. It is still accepted for
compatibility and is only sent when you pass it.

### Score-first music (v3)

AudioMusic v3 writes the song as an editable score (ABC notation) first and
renders the audio from that score, so you can read and change the music itself
before paying for a recording. There is no `duration`: length follows the
lyrics and the score.

```python
caps = client.music.v3_availability()  # {"available": bool, "revise": bool}
if caps["available"]:
    # 1. Write the score only (no audio). Bring your own lyrics, or describe
    #    the song and AudioPod writes the lyrics first.
    plan = client.music.compose(
        description="a hopeful folk song about leaving a harbour town at dawn",
        target_seconds=150,
        wait_for_completion=True,
    )

    # 2. Optional: change it in plain English (when enabled for your account)
    if caps.get("revise"):
        plan = client.music.revise_score(
            source_job_id=plan["job_id"],
            instruction="make the chorus higher",
            section="chorus",
            idempotency_key="my-retry-safe-key",
            wait_for_completion=True,
        )
        print(plan["note"], plan["score_comparison"]["changed_bars"])  # {"Vocal": [[9, 16]]}

    # 3. Record the score as audio (omit abc to record the score as it is)
    song = client.music.record_score(source_job_id=plan["job_id"], wait_for_completion=True)
    print(song["audio_url"])
```

| Method | Endpoint |
|---|---|
| `v3_availability()` | `GET /api/v1/music/v3/availability` |
| `compose(style=None, lyrics=None, description=None, target_seconds=None, language=None, ...)` | `POST /api/v1/music/v3/plan` (score only) |
| `revise_score(source_job_id, instruction, section=None, bars=None, idempotency_key=None, ...)` | `POST /api/v1/music/v3/revise` (score only) |
| `record_score(source_job_id, abc=None, ...)` | `POST /api/v1/music/v3/edit` (renders audio) |
| `generate_v3(style, lyrics=None, abc=None, ...)` | `POST /api/v1/music/v3/generate` (score + audio) |
| `get_v3_job(job_id)` / `get_score(job_id)` | `GET /api/v1/music/v3/jobs/{id}` / `.../score` |
| `list_v3_jobs(workflow=None, source_job_id=None)` | `GET /api/v1/music/v3/jobs` |
| `wait_for_v3_job(job_id)` | polls until `COMPLETED` |

Checked client-side before any request (`ValidationError`): `lyrics` and
`description` are mutually exclusive, `style` is required without a
`description`, `target_seconds` is 30–300, `instruction` is 1–500 characters,
`section` at most 60, `bars` 1–10000 with start ≤ end, and `idempotency_key`
(sent as the `Idempotency-Key` header) at most 200.

Server error codes (in the `APIError` message; nothing is charged for any of
them): `LYRICS_FAILED` (422), `LYRICS_BUSY` (503), `DESCRIPTION_NOT_ALLOWED`
(422) on `compose`; `REVISE_FAILED` (422), `REVISE_TARGET_NOT_FOUND` (422),
`REVISE_IN_FLIGHT` (409), `IDEMPOTENCY_KEY_REUSED` (422), `REVISE_RATE_LIMITED`
(429), `REVISE_UNAVAILABLE` (503) on `revise_score`; `SCORE_ALREADY_RECORDING`
(409) on `record_score`.

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
project = client.audiobook.create_project(title="My Book", author="J. Doe")
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
except AuthenticationError as e:
    print(e)  # says to set AUDIOPOD_API_KEY and where to create a key
except InsufficientBalanceError as e:
    print(e)  # explains the API wallet and how to top it up
    print(f"required {e.required_cents} cents, available {e.available_cents}")
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
