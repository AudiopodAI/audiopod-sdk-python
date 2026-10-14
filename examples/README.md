# AudioPod Python SDK examples

Small, runnable programs that each end with a real AudioPod call. Every one
reads your key from `AUDIOPOD_API_KEY`
([get a key](https://www.audiopod.ai/dashboard/account/api-keys); new accounts
start with free credits).

| Example | What it does |
|---|---|
| [`fastapi-transcribe/`](fastapi-transcribe/) | A FastAPI service: `POST /transcribe` with an audio URL returns a speaker-labelled transcript; `GET /transcribe/{job_id}/subtitles.srt` returns SRT. |
| [`stems-cli/`](stems-cli/) | `python stems.py song.mp3 --mode four` splits a song and saves each stem to a folder. |

Guides for every task: [docs.audiopod.ai/quickstarts](https://docs.audiopod.ai/quickstarts/transcription).
Using an AI coding agent? See [AudioPod for AI agents](https://docs.audiopod.ai/agents).
