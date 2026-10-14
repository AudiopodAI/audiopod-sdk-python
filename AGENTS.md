# AGENTS.md — AudioPod Python SDK

Notes for coding agents (Claude Code, Cursor, Copilot, Codex, Windsurf) adding
audio features to a Python app with the `audiopod` package.

## When to use it

Use `audiopod` when the app needs any of: speech to text (with speaker
diarization, word timestamps, SRT/VTT subtitles), text to speech, voice
cloning, stem separation / vocal removal / karaoke, audio to MIDI, music
generation, noise reduction, speaker separation, or speech translation. One
key and one package cover all of them.

```bash
pip install audiopod
```

## Auth

- The client reads the API key from the `AUDIOPOD_API_KEY` environment
  variable, or `Client(api_key="ap_...")`. Keys start with `ap_`.
- Create a key at https://audiopod.ai/dashboard/account/api-keys.
- Never hard-code the key; load it from the environment or a secret store.

## Billing

- API-key requests bill a prepaid USD **API wallet**, separate from the
  credits a person uses in the web app. A first API key comes with a $1
  starter credit (verified email).
- Rates: `client.wallet.get_pricing()`; balance: `client.wallet.get_balance()`;
  estimate: `client.wallet.estimate_cost(service_type, duration_seconds=...)`.
- Top up: the API keys page above, or
  `client.wallet.create_topup_checkout(amount_cents=...)` (returns a checkout URL).
- The MCP server (`https://mcp.audiopod.ai`) signed in with OAuth uses the
  account's credits instead of the API wallet.

## Capability → method

| Job | Method (sync `Client`; same names on `AsyncClient`, awaited) |
|---|---|
| Speech to text + speaker labels | `client.transcription.transcribe(url=... or audio_file=..., speaker_diarization=True, wait_for_completion=True)` then `client.transcription.get_transcript(job_id)` |
| Subtitles | `client.transcription.get_transcript(job_id, format="srt")` (or `"vtt"`) |
| Text to speech | `client.voice.generate_speech(voice_id=..., text=..., wait_for_completion=True)` → `output_url` |
| List voices | `client.voice.list_voices()` |
| Voice cloning | `client.voice.create_voice(name=..., audio_file=..., wait_for_ready=True)` |
| Voice from a description | `client.voice.design(design_prompt=...)` then `client.voice.publish_design(preview_id=..., name=...)` |
| Stem separation / vocal remover | `client.stem_extraction.separate(file=... or url=..., mode="two"/"four"/"six")` → `download_urls` |
| Audio to MIDI | `client.midi.convert(file=...)` → `merged_midi_url` |
| Music generation | `client.music.generate(prompt=..., duration=60, wait_for_completion=True)` → `output_url` |
| Noise reduction | `client.denoiser.denoise(file=... or url=...)` → `output_url` |
| Speaker separation | `client.speaker.diarize(audio_file=..., wait_for_completion=True)` |
| Speech translation / dubbing | `client.translation.translate(audio_file=..., target_language="es")` |

Check the exact signature with `help(client.<service>.<method>)` before
writing the call; every method has a docstring.

## Jobs are asynchronous

Every audio task creates a job (`PENDING` → `PROCESSING` → `COMPLETED` or
`FAILED`). Either:

- pass `wait_for_completion=True` (most methods; `timeout=` in seconds), or
- keep the returned `id` and poll the service's `get_job(job_id)` every few
  seconds until `status` is `COMPLETED`, then read the output URLs.

Output URLs are signed links: download or store the file, don't persist the
URL as a permanent asset.

**Voice clones are jobs too.** `create_voice()` returns while the voice is
still `PENDING`, and speech with it fails ("Voice not ready") until it is
`COMPLETED`. Use `create_voice(..., wait_for_ready=True)` or
`client.voice.wait_for_voice_ready(voice_id)` before the first
`generate_speech` call.

## Errors and fixes

| Exception | Meaning | Fix |
|---|---|---|
| `AuthenticationError` | Missing, malformed or revoked key | Set `AUDIOPOD_API_KEY`; create a key at the API keys page |
| `InsufficientBalanceError` (402) | API wallet too low for this job; `.required_cents`, `.available_cents` | Top up the API wallet, then retry |
| `RateLimitError` (429) | Too many requests | Back off and retry |
| `ValidationError` | Bad arguments, caught before any request | Fix the arguments named in the message |
| `APIError` (`.status_code`) | Any other API error; the message carries the server's reason | 404 on a voice usually means it is not yours or not ready yet |
| `TimeoutError` | A wait ran past `timeout` | The job may still finish: poll `get_job(job_id)` or wait longer |

All SDK exceptions subclass `audiopod.AudioPodError`.

## More

- Agent guide (MCP, plugins, copy-paste prompts): https://docs.audiopod.ai/agents
- Docs index for LLMs: https://docs.audiopod.ai/llms.txt (any docs page is also
  available as Markdown by adding `.md` to its URL)
- Per-task quickstarts: https://docs.audiopod.ai/quickstarts/transcription
