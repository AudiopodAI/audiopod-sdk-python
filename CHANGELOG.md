# Changelog

## 2.10.0

### Added — Score-first music (v3)

New `client.music` methods for AudioMusic v3, where the song is written as an
editable score (ABC notation) first and the audio is rendered from it:

- `v3_availability()` — whether v3 is offered.
- `compose(...)` — write a score only, no audio (`POST /music/v3/plan`).
- `revise_score(...)` — revise a score from a plain-language instruction
  (`POST /music/v3/revise`, coming soon on the server; 404 until then).
  `instruction` is limited to 500 characters client-side.
- `record_score(...)` — render audio from a complete score (`POST /music/v3/edit`).
- `generate_v3(...)` — score and audio in one call (`POST /music/v3/generate`).
- `get_v3_job()`, `get_score()`, `list_v3_jobs()`, `wait_for_v3_job()`.

`compose` also accepts `description` (mutually exclusive with `lyrics`),
`target_seconds` and `language`; these are coming soon on the server and are
rejected (422) until then. They are only sent when you pass them.

### Changed

- The `quality` argument on the v2 music methods is deprecated and no longer
  needed: every plan now gets the highest-quality music model at the standard
  rate. It is still accepted and is only sent when passed explicitly.
- `audiopod.__version__` now matches the package version.
