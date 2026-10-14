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
    client = _client(args)
    # Wait until the clone is usable: speech with a PENDING voice fails.
    voice = client.voice.create_voice(
        name=args.name,
        audio_file=args.reference,
        description=args.description or None,
        wait_for_ready=True,
        timeout=args.timeout,
    )
    _print(args, voice)


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
    p_cl.add_argument("--timeout", type=int, default=300)
    p_cl.set_defaults(func=cmd_clone)

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
        sys.stderr.write(f"auth error: {exc}\n")
        sys.exit(2)
    except (AudioPodError, TimeoutError) as exc:
        # The SDK's waits raise the built-in TimeoutError.
        sys.stderr.write(f"audiopod: {exc}\n")
        sys.exit(1)
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
