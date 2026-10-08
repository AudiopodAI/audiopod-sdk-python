# Changelog

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
