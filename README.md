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

[![Run in Postman](https://run.pstmn.io/button.svg)](https://god.gw.postman.com/run-collection/58401244-916ddbda-1a70-4c07-8ccd-fe524703a84b?action=collection%2Ffork&source=rip_markdown&collection-url=entityId%3D58401244-916ddbda-1a70-4c07-8ccd-fe524703a84b%26entityType%3Dcollection%26workspaceId%3D8013472d-5897-47d1-bf5c-92683a027b35&utm_source=audiopod-sdk-python)

Want to see a response before installing anything? The **Getting Started**
collection reaches a real `200` in two requests with no account and no API key.
[More about the collections](https://docs.audiopod.ai/sdks/postman).

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

### Effective voice settings and contextual auditions

The voice foundations endpoints require a server version that supports them.
`client.voice.capabilities(voice_id, operation="audition")` returns caller-specific
readiness, supported settings and timing facts. Treat `unknown` as a reason to
recheck; UI locale and speech language are separate.

```python
voice_id = 368  # Explicitly choose an authorized voice from list_voices().
capability = client.voice.capabilities(voice_id, operation="audition")
if capability["readiness"]["state"] != "ready":
    raise RuntimeError(capability["readiness"]["reason_code"])
context = {"text": "नमस्ते राकेश", "language": "hi"}
quote = client.voice.quote_audition(voice_id, **context)
# Display the quoted required_credits or cost_cents and obtain confirmation.
from uuid import uuid4
idempotency_key = str(uuid4())  # Retain for retries of this confirmation.
audition = client.voice.audition(
    voice_id, **context, quote_identity=quote["quote_identity"],
    idempotency_key=idempotency_key, confirm=True,
)
```

The same methods are awaitable through `AsyncClient`. Quotes do not generate
audio; accepted auditions use canonical existing speech charges. A `409` requires
a new quote and confirmation, not an automatic retry. Charged POST requests are
no longer automatically retried by the synchronous transport after a lost
response; inspect job state before deciding whether to submit another request.

Caller-owned `get_pronunciation`, `set_pronunciation`, `reset_pronunciation` and
`resolve_pronunciation` take an explicit language and optional project scope.
Save/reset uses `expected_version`. Reset restores inheritance; `mode="disable"`
disables rules. Resolve returns the exact spoken text and `snapshot.identity`;
pass that as `pronunciation_identity` to `generate_speech` alongside the same
`pronunciation_project_kind` / `pronunciation_project_id` to reject stale rules.
Printed text and the existing billing text basis remain unchanged.

`reference_diagnostics(audio_file, crop_start_seconds, crop_end_seconds)` measures
the exact window without ASR, clone registration or a credit charge. Acoustic
facts and raw/window/prepared digests are separate from `transcript_validation`;
none of these establishes the speaker's identity.

### Exact-reference consent and recovery

New clones require accepted consent and exact-reference admission. The legacy
`create_voice` request is deprecated and current servers reject it; existing
stored voices remain usable. Measure a 3–15 second crop of the original file,
show the recording/scope/policy, then obtain explicit confirmation:

```python
from audiopod import VOICE_CONSENT_VERSION
from uuid import uuid4
owner = Client(access_token=signed_in_jwt)
audio_file = "original.wav"
facts = owner.voice.reference_diagnostics(audio_file, 0, 10)
if not facts["prepared_sha256"]:
    raise RuntimeError("Choose a usable reference")
# Only after the signed-in owner accepts this exact recording and policy:
receipt = owner.voice.create_consent({
    "project_kind": "account", "recording_sha256": facts["raw_sha256"],
    "window_sha256": facts["window_sha256"],
    "prepared_sha256": facts["prepared_sha256"], "crop": facts["crop"],
    "reference_filename": "original.wav",
    "consent_version": VOICE_CONSENT_VERSION, "confirm": True,
})
admission = client.voice.admit_reference(
    audio_file, consent_id=receipt["id"], consent_revision=receipt["consent_revision"],
    consent_version=receipt["consent_version"],
    transcription="The exact words spoken in the selected crop.",
    confirm_transcription=True,  # Authorize exact-window ASR validation explicitly.
)
clone_key = str(uuid4())  # Store before submitting; retain after uncertainty.
registration = client.voice.register_reference(
    audio_file, admission_token=admission["admission_token"],
    idempotency_key=clone_key, name="My Voice", language_code="en",
)
# Processing/registration_uncertain/cleanup_pending require recovery reads:
status = client.voice.registration_status(clone_key)
if status["state"] == "completed" and status["voice_id"] is not None:
    capability = client.voice.capabilities(status["voice_id"], operation="tts")
    if capability["readiness"]["state"] == "ready":
        client.voice.generate_speech(status["voice_id"], "Now in my own voice.")
```

Admission and registration receive the same original file; the receipt fixes the
crop. For replacement, pass `replace_voice_id` and the current numeric
`reference_revision` to admission. A stale revision requires fresh review; a
failed replacement preserves the previous reference. Read recovery with the
retained UUID instead of submitting a new clone after an uncertain response.

For a named speaker, create consent with `recipient_email` and manually share the
invitation token and recording. The named signed-in recipient uses
`preview_consent_invitation` then explicitly `accept_consent_invitation`. No email
is sent. API keys can consume a prior accepted owner grant but cannot grant
consent. Transcript correspondence does not establish identity or liveness.

New clones are private. Self/account consent may optionally include explicit
`allow_public_sharing=True`; a later owner `update_metadata(id, {"is_public": True})`
is a separate action. Named, project and source grants stay private. Metadata
also supports name, description, gender, age_group and use_case.

Dubbing source consent binds `project_kind="dubbing"`, exact `project_id` and
`source_id`. Registration requires a live confirmed workflow hold and uses it,
without an SDK component charge. Retrieve scoped voices with
`dubbing.project_voices(project_id)`; they cannot enter general TTS or other
projects. Check operation capabilities: audiobook, conversion and direct
streaming currently reject unsupported strict references before billing.

Voice conversion (voice-to-voice) is available via the REST API — see
[Voice Changer](https://docs.audiopod.ai/api-reference/voice-changer).


## Reviewed dubbing and private reuse

These methods require a backend version with the dubbing and strict-consent
routes. Upload admission uses the original source bytes and server measurement;
no SDK duration estimate determines price. Presigned uploads are one PUT using
only the returned storage headers. They do not send API credentials or follow
redirects. There is no separate completion or multipart-resume endpoint.

```python
from pathlib import Path
from uuid import uuid4
file = Path("original.wav")
client.uploads.limits("dubbing")
upload = client.uploads.presign({
    "service": "dubbing", "filename": file.name, "content_type": "audio/wav",
    "size_bytes": file.stat().st_size,
})
client.uploads.put(upload, str(file))
source = client.dubbing.adopt_source(upload["upload_id"])
# If preparing, poll get_source(source["id"]) before creating a project.
if source["status"] != "ready":
    raise RuntimeError("Source admission is not ready")
project = client.dubbing.create_project({
    "source_id": source["id"], "title": "Hindi edition", "source_language": "en",
})
edition = client.dubbing.create_edition(project["id"], {
    "target_language": "hi", "settings": {"catalog_voice_id": 368},
    "required_outputs": ["audio", "srt"],
})
quote = client.dubbing.quote(edition["id"])
# Show this account-credit quote and obtain explicit confirmation first.
key = str(uuid4())  # Persist with this exact quote before submitting.
accepted = client.dubbing.analyze(project["id"], {
    "confirm": True, "confirmations": [{"edition_id": edition["id"],
        "expected_revision": quote["revision"], "quote_identity": quote["quote_identity"],
        "idempotency_key": key}],
})
reviewed = client.dubbing.wait_for_job(accepted["items"][0]["id"])
# review_required: inspect/edit/save the edition before a new decision.
# After review, obtain a fresh quote and explicitly confirm generation:
generation = client.dubbing.quote(edition["id"])
job = client.dubbing.generate(reviewed["id"], {
    "expected_revision": generation["revision"],
    "quote_identity": generation["quote_identity"], "confirm": True,
})
result = client.dubbing.wait_for_job(job["id"])
# export_partial requires an explicit retry_exports/cancel decision.
# completed + captured artifacts may be fetched with artifact(job["id"], "audio").
```

All service methods are awaitable on `AsyncClient`. `wait_for_job` returns at
`review_required`, `export_partial` and `completed`, without generating,
retranslating or retrying exports. Failed/cancelled/expired jobs raise `APIError`
with the job and error code retained in `detail`.

| Area | Methods |
| --- | --- |
| Source/library | `adopt_source`, `get_source`, `source_media`, `create_project`, `list_projects`, `get_project`, `delete_project`, `project_voices` |
| Revision/work | `create_edition`, `get_edition`, `save_edition`, `quote`, `analyze`, `get_job`, `generate`, `retranslate`, `cancel`, `retry_exports`, `events`, `artifact`, `review_complete` |
| Private organization | `list_folders`, `create_folder`, `rename_folder`, `delete_folder`, `move_project` |
| Translation policy | `get_glossary`, `set_glossary`, `reset_glossary` with language/project scope and observed version |
| Reusable settings | `list_templates`, `save_template`, `from_template` with a new explicit source/voice selection |
| Named review | `invite_reviewer`, `list_review_grants`, `revoke_review_grant`, `get_review`, `add_comment`, `approve_review`, `list_review_comments`, `review_media` |

Typed requests/responses are in `audiopod.workflow_contracts`. Library filters are
folder_id/unfiled/review/completion. Templates copy safe settings, not voice
consent or paid authorization. Share review invitations manually. Use an explicit
`Client(access_token=...)` or `AsyncClient(access_token=...)` for signed-in grants
and named review; API keys do not become recipient identities. Media remains
authenticated.

Translation-only reruns use `quote(edition_id, retranslate=True)`. A held review
uses explicit `retranslate(job_id, {"expected_revision": ..., "quote_identity": ...,
"confirm": True})` on the same hold/deadline. A completed edition uses a newly
confirmed analyze item with `retranslate=True` and a new UUID. The server reuses
ASR and quotes the union of saved original intervals; the SDK does not calculate
or substitute prices.

HTTP errors retain `status_code`, `code`, `action`, `detail` and `retry_after`.
Stale quote/revision/consent errors require a fresh review. Persist accepted job
IDs, exact bodies and idempotency UUIDs before sending charged requests. POSTs
are never automatically retried, even with `max_retries` configured.

## CLI workflow actions

Both SDK CLIs use the same action names. Set `AUDIOPOD_API_KEY` for API work or
`AUDIOPOD_ACCESS_TOKEN` for signed-in consent/review; they are separate identities.
`--body FILE` supplies the exact JSON request. Paid/consent/approval actions require
`--confirm`; it does not fetch a replacement quote or choose a price.

```sh
audiopod dubbing capabilities --json
audiopod uploads presign --body upload.json --json
audiopod uploads put original.wav --body presigned.json --json
audiopod dubbing adopt-source UPLOAD_UUID --json
audiopod dubbing create-project --body project.json --json
audiopod dubbing create-edition PROJECT_UUID --body edition.json --json
audiopod dubbing quote EDITION_UUID --json
audiopod dubbing analyze PROJECT_UUID --body confirmed-batch.json --confirm --json
audiopod dubbing wait JOB_UUID --json
audiopod dubbing generate JOB_UUID --body confirmed-generation.json --confirm --json
audiopod dubbing artifact JOB_UUID audio --out localized.wav
audiopod dubbing quote EDITION_UUID --retranslate --json
audiopod dubbing retranslate JOB_UUID --body confirmed-generation.json --confirm --json
audiopod voice diagnostics original.wav --crop-start 0 --crop-end 10 --json
audiopod voice consent-create --body consent.json --confirm --json
audiopod voice admit original.wav --body admission.json --confirm --json
audiopod clone original.wav --name Narrator --admission-token TOKEN --idempotency-key UUID
audiopod voice clone-status UUID --json
```

`confirmed-batch.json` contains `confirmations` items with edition_id,
expected_revision, quote_identity and caller-generated UUID idempotency_key;
`confirmed-generation.json` contains expected_revision and quote_identity.
Retain the same UUID/body after transport uncertainty. A fresh intentional job
uses a new UUID. `--json` errors go to stderr with status/code/action/detail.

Dubbing actions also cover projects/project/project-voices/delete-project,
source/source-media, edition/save-edition, job/cancel/retry-exports/events,
review-complete, folders/create-folder/rename-folder/delete-folder/move-project,
glossary/set-glossary/reset-glossary, templates/save-template/from-template,
invite-reviewer/review-grants/revoke-review-grant/review/add-comment/approve-review/
review-comments/review-media. Binary media actions require `--out`.

Voice actions cover capabilities, diagnostics, consent/consent-preview/
consent-accept/consent-revoke, admit/clone-status/metadata, pronunciation/
pronunciation-save/pronunciation-reset/pronunciation-resolve, audition-quote/
audition-accept. Policy saves use `{"scope": {...}, "policy": {...}}`; policy resets
use `{"scope": {...}, "expected_version": N}`. Glossary scope uses language and
optional project_id; pronunciation scope also uses project_kind. Read/resolve
commands do not accept paid quotes automatically.

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

# Audiobook production (manuscript → ACX-ready export)
project = client.audiobook.create_project(title="My Book", author="Jane Doe")
```

The legacy `client.translation.translate` speech-dubbing route is deprecated and
unsupported. `/audio/translations` produces speech-to-English text; it does not
produce translated speech audio. Keep these contracts distinct from dubbing.

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
