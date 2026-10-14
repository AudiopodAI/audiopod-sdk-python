"""Split a song into stems and save each one next to it.

    pip install audiopod requests
    export AUDIOPOD_API_KEY=ap_...
    python stems.py song.mp3                 # vocals, drums, bass, other
    python stems.py song.mp3 --mode two      # vocals + instrumental (karaoke)
    python stems.py song.mp3 --mode six      # adds guitar and piano
"""

import argparse
import pathlib
import sys
from urllib.parse import urlparse

import requests

from audiopod import Client
from audiopod.exceptions import AudioPodError

MODES = ["two", "four", "six", "producer", "studio", "mastering"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Split a song into stems with AudioPod.")
    parser.add_argument("file", type=pathlib.Path, help="audio file to split")
    parser.add_argument("--mode", choices=MODES, default="four")
    parser.add_argument("--out", type=pathlib.Path, help="output folder (default: <file>_stems)")
    args = parser.parse_args()

    if not args.file.is_file():
        parser.error(f"{args.file} is not a file")
    out = args.out or args.file.with_name(f"{args.file.stem}_stems")
    out.mkdir(parents=True, exist_ok=True)

    client = Client()  # reads AUDIOPOD_API_KEY
    print(f"Separating {args.file.name} ({args.mode})...")
    try:
        job = client.stem_extraction.separate(file=str(args.file), mode=args.mode)
    except AudioPodError as exc:
        print(f"AudioPod error: {exc}", file=sys.stderr)
        return 1

    for stem, link in (job.get("download_urls") or {}).items():
        suffix = pathlib.PurePosixPath(urlparse(link).path).suffix or ".wav"
        target = out / f"{stem}{suffix}"
        with requests.get(link, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(target, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 16):
                    fh.write(chunk)
        print(f"  {stem:<12} -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
