"""FastAPI service: POST an audio URL, get a speaker-labelled transcript back.

Run:
    pip install -r requirements.txt
    export AUDIOPOD_API_KEY=ap_...
    uvicorn main:app --reload

Try:
    curl -X POST localhost:8000/transcribe \
      -H 'Content-Type: application/json' \
      -d '{"url": "https://example.com/interview.mp3"}'
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from audiopod import Client
from audiopod.exceptions import AudioPodError

app = FastAPI(title="Transcribe with AudioPod")
client = Client()  # reads AUDIOPOD_API_KEY


class TranscribeRequest(BaseModel):
    url: str
    language: Optional[str] = None  # detected automatically when omitted


class Segment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str


class TranscribeResponse(BaseModel):
    job_id: int
    segments: List[Segment]


def _transcribe(url: str, language: Optional[str]) -> TranscribeResponse:
    job = client.transcription.transcribe(
        url=url,
        language=language,
        speaker_diarization=True,
        wait_for_completion=True,
    )
    transcript = client.transcription.get_transcript(job["id"])
    return TranscribeResponse(
        job_id=job["id"],
        segments=[
            Segment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                speaker=seg.get("speaker_label") or "",
                text=(seg.get("text") or "").strip(),
            )
            for seg in transcript.get("segments", [])
        ],
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(req: TranscribeRequest) -> TranscribeResponse:
    try:
        # The SDK call blocks while the job runs, so keep it off the event loop.
        return await run_in_threadpool(_transcribe, req.url, req.language)
    except AudioPodError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/transcribe/{job_id}/subtitles.srt", response_class=PlainTextResponse)
async def subtitles(job_id: int) -> str:
    """The finished job's segments as SRT subtitles, speaker in front of each line."""
    transcript = await run_in_threadpool(client.transcription.get_transcript, job_id)
    lines = []
    for i, seg in enumerate(transcript.get("segments", []), start=1):
        speaker = seg.get("speaker_label")
        text = (seg.get("text") or "").strip()
        lines += [
            str(i),
            f"{_ts(seg.get('start', 0.0))} --> {_ts(seg.get('end', 0.0))}",
            f"[{speaker}] {text}" if speaker else text,
            "",
        ]
    return "\n".join(lines)


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"
