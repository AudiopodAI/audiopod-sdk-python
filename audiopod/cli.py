"""
AudioPod CLI — generate music, voiceover, transcribe, separate stems, and
clone voices from the terminal.

Auth: ``audiopod login`` stores your API key at ``~/.audiopod/config.json``,
or set ``AUDIOPOD_API_KEY`` in the environment.

Examples:
    audiopod music "lo-fi rainy 90 BPM" --duration 60 --out song.wav
    audiopod tts "Welcome to AudioPod." --voice 368 --out hello.wav
    audiopod transcribe meeting.mp3 --diarize --format srt
    audiopod stems track.wav --mode six --out-dir stems/
    audiopod clone reference.wav --name Narrator
    audiopod jobs job_abc123
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import urlopen

from . import __version__
from .client import Client
from .exceptions import AudioPodError, AuthenticationError


CONFIG_DIR = Path.home() / ".audiopod"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ---- Config helpers ----


def _load_api_key() -> Optional[str]:
    env_key = os.environ.get("AUDIOPOD_API_KEY")
    if env_key:
        return env_key
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text())
        except json.JSONDecodeError:
            return None
        key = data.get("api_key")
        if isinstance(key, str) and key.startswith("ap_"):
            return key
    return None


def _save_api_key(api_key: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"api_key": api_key}, indent=2))
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def _client(args: argparse.Namespace) -> Client:
    token = getattr(args,"access_token",None) or os.environ.get("AUDIOPOD_ACCESS_TOKEN")
    if token:
        return Client(access_token=token,base_url=args.base_url,debug=args.debug)
    api_key = args.api_key or _load_api_key()
    if not api_key:
        sys.stderr.write(
            "No API key found. Run `audiopod login` or set AUDIOPOD_API_KEY.\n"
        )
        sys.exit(2)
    return Client(api_key=api_key, base_url=args.base_url, debug=args.debug)


# ---- Output helpers ----


def _print(args: argparse.Namespace, payload: Any) -> None:
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        if isinstance(payload, dict):
            for key, value in payload.items():
                print(f"{key}: {value}")
        else:
            print(payload)


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as resp, dest.open("wb") as fh:
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            fh.write(chunk)


def _wait_for_url(client: Client, job_id: Any, *, label: str, timeout: int) -> Dict[str, Any]:
    """Generic poll loop. Each service's status endpoint returns
    ``{"status": "...", "output_url": "..."}`` once complete."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = client.request(
                "GET", f"/api/v1/jobs/{job_id}", json_data=None
            )
        except AudioPodError:
            response = None  # noqa: F841 — fall through to per-service polling
        if response and isinstance(response, dict) and response.get("output_url"):
            return response
        time.sleep(2)
        sys.stderr.write(f"{label}: still working...\n")
    raise SystemExit(f"{label}: timed out after {timeout}s")


# ---- Commands ----


def cmd_login(args: argparse.Namespace) -> None:
    if args.api_key:
        api_key = args.api_key
    else:
        sys.stderr.write(
            "Paste your AudioPod API key (create one at https://audiopod.ai/dashboard/api-keys):\n"
        )
        api_key = getpass("API key: ").strip()
    if not api_key.startswith("ap_"):
        sys.stderr.write("API keys start with 'ap_'.\n")
        sys.exit(2)
    _save_api_key(api_key)
    print(f"Saved to {CONFIG_FILE}")


def cmd_music(args: argparse.Namespace) -> None:
    client = _client(args)
    task_map = {
        "song": "text2music",
        "instrumental": "prompt2instrumental",
        "rap": "text2rap",
        "vocals": "lyric2vocals",
    }
    task = task_map.get(args.kind, "text2music")
    job = client.music.generate(
        prompt=args.prompt,
        task=task,
        duration=args.duration,
        lyrics=args.lyrics,
        wait_for_completion=bool(args.out),
        timeout=args.timeout,
    )
    if args.out and isinstance(job, dict) and job.get("output_url"):
        _download(job["output_url"], Path(args.out))
        print(f"Saved {args.out}")
    else:
        _print(args, job)


def cmd_tts(args: argparse.Namespace) -> None:
    client = _client(args)
    job = client.voice.generate_speech(
        voice_id=args.voice,
        text=args.text,
        speed=args.speed,
        language=args.lang,
        audio_format=args.format,
        wait_for_completion=bool(args.out),
        timeout=args.timeout,
    )
    if args.out and isinstance(job, dict) and job.get("output_url"):
        _download(job["output_url"], Path(args.out))
        print(f"Saved {args.out}")
    else:
        _print(args, job)


def cmd_transcribe(args: argparse.Namespace) -> None:
    client = _client(args)
    job = client.transcription.transcribe(
        source=args.source,
        language=args.lang,
        diarize=args.diarize,
        wait_for_completion=True,
        timeout=args.timeout,
    )
    if args.out and isinstance(job, dict) and job.get("transcript_url"):
        _download(job["transcript_url"], Path(args.out))
        print(f"Saved {args.out}")
    else:
        _print(args, job)


def cmd_stems(args: argparse.Namespace) -> None:
    client = _client(args)
    mode_map = {
        "two": "2stem_vocals",
        "four": "4stem",
        "six": "6stem",
        "sixteen": "16stem",
    }
    mode = mode_map.get(args.mode, "4stem")
    job = client.stems.extract(
        source=args.source,
        mode=mode,
        wait_for_completion=True,
        timeout=args.timeout,
    )
    _print(args, job)


def cmd_clone(args: argparse.Namespace) -> None:
    if not args.admission_token or not args.idempotency_key:
        raise ValueError("Clone requires --admission-token and retained --idempotency-key UUID")
    client = _client(args)
    voice = client.voice.register_reference(
        args.reference,
        name=args.name,
        admission_token=args.admission_token,
        idempotency_key=args.idempotency_key,
        language_code=args.language,
    )
    _print(args, voice)


def _workflow_body(args):
    body = json.loads(Path(args.body).read_text()) if args.body else {}
    if not isinstance(body,dict): raise ValueError("--body must contain a JSON object")
    return body


def _require_confirm(args):
    if not args.confirm: raise ValueError("Explicit --confirm is required; first inspect the current quote or consent")


def cmd_dubbing(args):
    action, identifier, extra = args.action, args.identifier, args.extra
    if action in ("analyze","generate","retranslate","approve-review"): _require_confirm(args)
    body = _workflow_body(args)
    api = _client(args).dubbing
    actions = {
        "capabilities":lambda:api.capabilities(),"adopt-source":lambda:api.adopt_source(identifier),"source":lambda:api.get_source(identifier),
        "create-project":lambda:api.create_project(body),"projects":lambda:api.list_projects(**body),"project":lambda:api.get_project(identifier),
        "delete-project":lambda:api.delete_project(identifier),"project-voices":lambda:api.project_voices(identifier),
        "create-edition":lambda:api.create_edition(identifier,body),"edition":lambda:api.get_edition(identifier),"save-edition":lambda:api.save_edition(identifier,body),
        "quote":lambda:api.quote(identifier,retranslate=args.retranslate),"analyze":lambda:api.analyze(identifier,{**body,"confirm":True}),
        "job":lambda:api.get_job(identifier),"generate":lambda:api.generate(identifier,{**body,"confirm":True}),"retranslate":lambda:api.retranslate(identifier,{**body,"confirm":True}),
        "cancel":lambda:api.cancel(identifier),"retry-exports":lambda:api.retry_exports(identifier),"events":lambda:api.events(identifier,args.after),
        "wait":lambda:api.wait_for_job(identifier,timeout=args.timeout),"review-complete":lambda:api.review_complete(identifier,body["expected_revision"]),
        "folders":lambda:api.list_folders(),"create-folder":lambda:api.create_folder(**body),"rename-folder":lambda:api.rename_folder(identifier,**body),"delete-folder":lambda:api.delete_folder(identifier),
        "move-project":lambda:api.move_project(identifier,body["folder_id"]),"glossary":lambda:api.get_glossary(**body),
        "set-glossary":lambda:api.set_glossary(body["scope"]["language"],body["policy"],body["scope"].get("project_id")),
        "reset-glossary":lambda:api.reset_glossary(body["scope"]["language"],body["expected_version"],body["scope"].get("project_id")),
        "templates":lambda:api.list_templates(),"save-template":lambda:api.save_template(identifier,body["label"]),"from-template":lambda:api.from_template(body),
        "invite-reviewer":lambda:api.invite_reviewer(identifier,body["recipient_email"]),"review-grants":lambda:api.list_review_grants(identifier),"revoke-review-grant":lambda:api.revoke_review_grant(identifier),
        "review":lambda:api.get_review(identifier),"add-comment":lambda:api.add_comment(identifier,body),"approve-review":lambda:api.approve_review(identifier,body["expected_revision"]),
        "review-comments":lambda:api.list_review_comments(identifier),
    }
    media = {"source-media":lambda:api.source_media(identifier),"artifact":lambda:api.artifact(identifier,extra),"review-media":lambda:api.review_media(identifier,extra)}
    if action in media:
        if not args.out: raise ValueError("Media commands require --out")
        Path(args.out).write_bytes(media[action]())
        _print(args,{"path":args.out})
    else:
        if action not in actions: raise ValueError("Unknown dubbing action")
        _print(args,actions[action]())


def cmd_voice_workflow(args):
    action, identifier = args.action,args.identifier
    body = _workflow_body(args)
    if action in ("consent-create","consent-accept","admit","audition-accept"): _require_confirm(args)
    api = _client(args).voice
    actions = {
        "capabilities":lambda:api.capabilities(identifier,args.operation),
        "diagnostics":lambda:api.reference_diagnostics(identifier,args.crop_start,args.crop_end),
        "consent-create":lambda:api.create_consent({**body,"confirm":True}),"consent":lambda:api.get_consent(identifier),
        "consent-preview":lambda:api.preview_consent_invitation(identifier),
        "consent-accept":lambda:api.accept_consent_invitation(body["invitation_token"],body["consent_version"],confirm=True),
        "consent-revoke":lambda:api.revoke_consent(identifier,body["expected_revision"]),
        "admit":lambda:api.admit_reference(identifier,**{**body,"confirm_transcription":True}),
        "clone-status":lambda:api.registration_status(identifier),"metadata":lambda:api.update_metadata(identifier,body),
        "pronunciation":lambda:api.get_pronunciation(**body),
        "pronunciation-save":lambda:api.set_pronunciation(**{**body["scope"],**body["policy"]}),
        "pronunciation-reset":lambda:api.reset_pronunciation(**{**body["scope"],"expected_version":body["expected_version"]}),
        "pronunciation-resolve":lambda:api.resolve_pronunciation(**{**body["scope"],"text":body.get("text","")}),
        "audition-quote":lambda:api.quote_audition(identifier,**body),"audition-accept":lambda:api.audition(identifier,**{**body,"confirm":True}),
    }
    if action not in actions: raise ValueError("Unknown voice workflow action")
    _print(args,actions[action]())


def cmd_uploads(args):
    body = _workflow_body(args)
    api = _client(args).uploads
    if args.action == "limits": _print(args,api.limits(args.service))
    elif args.action == "presign": _print(args,api.presign(body))
    elif args.action == "put": _print(args,api.put(body,args.identifier))
    else: raise ValueError("Unknown uploads action")


def cmd_audiobook(args: argparse.Namespace) -> None:
    client = _client(args)
    result = client.audiobook.produce(
        title=args.title,
        author=args.author,
        file=args.file,
        text=args.text,
        voice_id=int(args.voice),
        timeout=args.timeout,
    )
    if args.out and isinstance(result, dict) and result.get("download_url"):
        _download(result["download_url"], Path(args.out))
        print(f"Saved {args.out}")
    else:
        _print(args, result)


def cmd_jobs(args: argparse.Namespace) -> None:
    client = _client(args)
    response = client.request("GET", f"/api/v1/jobs/{args.job_id}", json_data=None)
    _print(args, response)


# ---- Parser ----


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audiopod",
        description="AudioPod CLI — generate music, voice, transcribe, and more.",
    )
    parser.add_argument("--version", action="version", version=f"audiopod {__version__}")
    parser.add_argument("--access-token",help="Signed-in JWT for consent and named review; or AUDIOPOD_ACCESS_TOKEN.")
    parser.add_argument(
        "--api-key",
        default=None,
        help="Override the saved API key.",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AUDIOPOD_BASE_URL"),
        help="Override the API base URL (default https://api.audiopod.ai).",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit machine-readable JSON."
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging."
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_login = sub.add_parser("login", help="Store your API key in ~/.audiopod/config.json.")
    p_login.set_defaults(func=cmd_login)

    p_music = sub.add_parser("music", help="Generate music from a text prompt.")
    p_music.add_argument("prompt", help="Style / lyrics description.")
    p_music.add_argument(
        "--kind",
        default="song",
        choices=["song", "instrumental", "rap", "vocals"],
        help="Generation mode.",
    )
    p_music.add_argument("--duration", type=int, default=60)
    p_music.add_argument("--lyrics", default=None)
    p_music.add_argument("--out", default=None, help="Path to save the audio (waits for job).")
    p_music.add_argument("--timeout", type=int, default=600)
    p_music.set_defaults(func=cmd_music)

    p_tts = sub.add_parser("tts", help="Synthesize speech from text.")
    p_tts.add_argument("text", help="Text to read aloud.")
    p_tts.add_argument("--voice", default="368", help="Voice ID or name (default 368).")
    p_tts.add_argument("--lang", default="en")
    p_tts.add_argument("--speed", type=float, default=1.0)
    p_tts.add_argument("--format", default="mp3", choices=["mp3", "wav", "ogg"])
    p_tts.add_argument("--out", default=None)
    p_tts.add_argument("--timeout", type=int, default=300)
    p_tts.set_defaults(func=cmd_tts)

    p_tx = sub.add_parser("transcribe", help="Transcribe an audio/video file or URL.")
    p_tx.add_argument("source", help="Local path or URL.")
    p_tx.add_argument("--lang", default=None)
    p_tx.add_argument("--diarize", action="store_true")
    p_tx.add_argument("--format", default="text", choices=["text", "srt", "vtt", "json"])
    p_tx.add_argument("--out", default=None)
    p_tx.add_argument("--timeout", type=int, default=900)
    p_tx.set_defaults(func=cmd_transcribe)

    p_st = sub.add_parser("stems", help="Separate an audio file into stems.")
    p_st.add_argument("source", help="Local path or URL.")
    p_st.add_argument(
        "--mode",
        default="four",
        choices=["two", "four", "six", "sixteen"],
        help="Number of stems.",
    )
    p_st.add_argument("--timeout", type=int, default=900)
    p_st.set_defaults(func=cmd_stems)

    p_cl = sub.add_parser("clone", help="Clone a voice from a reference clip.")
    p_cl.add_argument("reference", help="Path to a 5–30s reference audio file.")
    p_cl.add_argument("--name", required=True)
    p_cl.add_argument("--description", default=None)
    p_cl.set_defaults(func=cmd_clone)
    p_cl.add_argument("--admission-token",help="Explicit exact-reference admission.")
    p_cl.add_argument("--idempotency-key",help="Retain this UUID for transport retries.")
    p_cl.add_argument("--language",default=None)

    for name, handler in (("dubbing",cmd_dubbing),("voice",cmd_voice_workflow),("uploads",cmd_uploads)):
        workflow = sub.add_parser(name,help="Public workflow actions; --body FILE supplies exact JSON.")
        workflow.add_argument("action")
        workflow.add_argument("identifier",nargs="?")
        workflow.add_argument("extra",nargs="?")
        workflow.add_argument("--body")
        workflow.add_argument("--confirm",action="store_true")
        workflow.add_argument("--out")
        workflow.add_argument("--retranslate",action="store_true")
        workflow.add_argument("--after",type=int,default=0)
        workflow.add_argument("--timeout",type=float,default=300)
        workflow.add_argument("--operation",default="tts")
        workflow.add_argument("--crop-start",type=float,default=0)
        workflow.add_argument("--crop-end",type=float)
        workflow.add_argument("--service",default="dubbing")
        workflow.add_argument("--json",action="store_true",default=argparse.SUPPRESS)
        workflow.add_argument("--api-key",default=argparse.SUPPRESS)
        workflow.add_argument("--access-token",default=argparse.SUPPRESS)
        workflow.add_argument("--base-url",default=argparse.SUPPRESS)
        workflow.set_defaults(func=handler)

    p_ab = sub.add_parser("audiobook", help="Produce an ACX audiobook from a manuscript (PDF/EPUB/DOCX/TXT).")
    p_ab.add_argument("file", nargs="?", default=None, help="Manuscript file. Omit and use --text to narrate raw text.")
    p_ab.add_argument("--title", required=True)
    p_ab.add_argument("--author", default=None)
    p_ab.add_argument("--text", default=None, help="Narrate this text instead of a file.")
    p_ab.add_argument("--voice", default="387", help="Narration voice ID (default 387).")
    p_ab.add_argument("--out", default=None, help="Download the ACX package ZIP to this path.")
    p_ab.add_argument("--timeout", type=int, default=1800)
    p_ab.set_defaults(func=cmd_audiobook)

    p_j = sub.add_parser("jobs", help="Look up an async job by id.")
    p_j.add_argument("job_id")
    p_j.set_defaults(func=cmd_jobs)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except AuthenticationError as exc:
        if args.json:
            sys.stderr.write(json.dumps({"error":{"message":str(exc),"status_code":exc.status_code,"code":exc.code,"action":exc.action,"detail":exc.detail,"retry_after":exc.retry_after}},default=str)+"\n")
            sys.exit(2)
        sys.stderr.write(f"auth error: {exc}\n")
        sys.exit(2)
    except AudioPodError as exc:
        if args.json:
            sys.stderr.write(json.dumps({"error":{"message":str(exc),"status_code":exc.status_code,"code":exc.code,"action":exc.action,"detail":exc.detail,"retry_after":exc.retry_after}},default=str)+"\n")
            sys.exit(1)
        sys.stderr.write(f"audiopod: {exc}\n")
        sys.exit(1)
    except (ValueError,KeyError,TypeError) as exc:
        sys.stderr.write(f"audiopod: {exc}\n")
        sys.exit(2)
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
