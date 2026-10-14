# Changelog

## Unreleased

### Added — `create_voice(..., wait_for_ready=True)` (PLAT-3976)

A new clone is `PENDING` while it processes, and speech with it fails until it
is `COMPLETED`. `create_voice` now takes `wait_for_ready` (default `False`),
`timeout` and `poll_interval`, and polls the voice status until it is usable;
a failed or cancelled clone raises `AudioPodError` with the reason. The poll is
also public as `client.voice.wait_for_voice_ready(voice_or_id)`. Sync and
async. `audiopod clone` waits too, and no longer crashes on an unknown
`files=` argument.

### Changed — 401 and 402 errors say how to fix them

`AuthenticationError` now says to set `AUDIOPOD_API_KEY` and where to create a
key. `InsufficientBalanceError` explains the prepaid API wallet and how to top
it up, and now reads the server's message and `required_cents` /
`available_cents` from the nested `detail` object (they were always `None`).
Exception classes are unchanged.

### Fixed — form requests without a file reach the API as a form (PLAT-3976)

Requests that send form fields but no file were posted with the client's
default `Content-Type: application/json`, so the API ignored every field.
`client.voice.generate_speech(...)` failed with 422 (`input_text` missing), and
URL-based `stem_extraction.separate(url=...)`, `midi.convert(url=...)`,
`denoiser.denoise(url=...)` and `speaker.diarize(url=...)` arrived without
their URL. The sync client now lets `requests` set the form content type, and
`AsyncClient` (which dropped the fields entirely) sends them urlencoded.

### Fixed — `denoiser.denoise(mode=...)` is honoured

The mode is now sent as the API's `quality_mode` field. It used to be sent as
`mode`, which the API ignored, so every job ran at the `"studio"` default.
`mode` now defaults to `None` (server default, `"studio"`), which keeps that
behaviour for callers that never set it.

### Fixed — `music.generate(..., wait_for_completion=True)` polls the right job

The create endpoints answer `{"job": {"id": N}, "message": ...}`; the SDK read
only a flat `id` / `job_id` and polled job `None`. Same fix for `instrumental`,
`song`, `rap`, `cover`, `reference` and `extract_stem`.

### Fixed — `speaker.diarize(num_speakers=...)` is honoured

The API reads `num_speakers` from the query string; it was sent as a form field
and dropped. Sync and async clients both send it as a query parameter now.

### Docs

README opens with a one-call quickstart per task and a "Using with AI agents"
section; `examples/` adds `fastapi-transcribe` and `stems-cli`.

## 2.10.1

### Fixed — an empty selection no longer means "the whole book" (PLAT-3944)

`auto_direct`, `batch_narrate`, `start_narration` and `start_export` (and the
wrappers built on them) now raise `ValueError` for an explicitly empty
`chapter_ids`, `paragraph_ids` or `include_chapters` list, e.g.
`chapter_ids is empty; pass None to use the whole book`. Previously
`auto_direct(chapter_ids=[])` dropped the list and directed the whole book
again. Pass `None` (or omit the argument) to use the whole book; the API itself
now rejects an empty list with 400 `empty_selection`.

## 2.10.0

### Added — Score-first music (v3)

New `client.music` methods for AudioMusic v3, where the song is written as an
editable score (ABC notation) first and the audio is rendered from it:

- `v3_availability()` — `{"available", "revise"}`: whether v3, and score
  revision, are offered for your account.
- `compose(...)` — write a score only, no audio (`POST /music/v3/plan`). Bring
  your own `lyrics`, or send a `description` (with optional `target_seconds`
  30–300 and `language`) and AudioPod writes the lyrics first.
- `revise_score(...)` — change a score in plain English (`POST /music/v3/revise`),
  narrowed by `section` or `bars`; returns a new score-only job whose
  `score_comparison.changed_bars` is `{voice: [[start, end], ...]}`. Available
  when enabled for your account. `idempotency_key` is sent as the
  `Idempotency-Key` header.
- `record_score(...)` — render audio from a score (`POST /music/v3/edit`). Omit
  `abc` to record the source job's score as it is (fetched via `get_score`).
- `generate_v3(...)` — score and audio in one call (`POST /music/v3/generate`).
- `get_v3_job()`, `get_score()`, `list_v3_jobs()`, `wait_for_v3_job()`.
- Client-side validation mirroring the server limits (`ValidationError`).
- `Client.request` / `AsyncClient.request` accept an optional `headers` dict.

### Changed

- The `quality` argument on the v2 music methods is deprecated and no longer
  needed: every plan now gets the highest-quality music model at the standard
  rate. It is still accepted and is only sent when passed explicitly.
- `audiopod.__version__` now matches the package version.
