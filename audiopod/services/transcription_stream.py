"""
Real-time streaming transcription over WebSocket.

Used via ``client.transcription.stream(...)`` on an :class:`AsyncClient`:

    import asyncio
    from audiopod import AsyncClient

    async def main():
        async with AsyncClient() as client:
            async with client.transcription.stream(language="en", diarize=True) as session:
                # Feed audio and read events concurrently for true real-time.
                async def feed():
                    for chunk in pcm_chunks:          # 16-bit PCM, 16 kHz, mono
                        await session.send_audio(chunk)
                    await session.end()

                asyncio.create_task(feed())
                async for event in session:
                    if event["type"] == "partial":
                        print("\\r" + event["text"], end="")
                    elif event["type"] == "final":
                        print("\\n" + event["text"])
                    elif event["type"] == "completed":
                        print(f"done — {event.get('credits_used')} credits")

    asyncio.run(main())

The first server frame is always ``{"type": "ready", ...}``. Streaming uses
premium accuracy and is prepaid: credits are reserved up front and settled to
the actual duration when the session ends.
"""

import json
from typing import Any, AsyncIterator, Dict, Optional

import aiohttp

_STREAM_PATH = "/api/v1/transcription/stream"


class TranscriptionStreamSession:
    """An async context manager + async iterator for a live transcription stream.

    Server frames are yielded as plain dicts with a ``type`` of ``ready``,
    ``partial``, ``final``, ``usage``, ``completed`` or ``error``.
    """

    def __init__(
        self,
        client: Any,
        *,
        language: Optional[str] = None,
        diarize: bool = False,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        self._client = client
        self._language = language
        self._diarize = diarize
        self._sample_rate = sample_rate
        self._channels = channels
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._closed = False

    def _ws_url(self) -> str:
        base = self._client.config.base_url
        if base.startswith("https://"):
            base = "wss://" + base[len("https://") :]
        elif base.startswith("http://"):
            base = "ws://" + base[len("http://") :]
        return base.rstrip("/") + _STREAM_PATH

    async def __aenter__(self) -> "TranscriptionStreamSession":
        self._session = aiohttp.ClientSession()
        # API key travels as a query param — WS handshakes can't carry our auth
        # headers from every client.
        self._ws = await self._session.ws_connect(
            self._ws_url(),
            params={"api_key": self._client.api_key},
            heartbeat=8.0,
        )
        await self._ws.send_str(
            json.dumps(
                {
                    "type": "start",
                    "language": self._language,
                    "diarize": self._diarize,
                    "sample_rate": self._sample_rate,
                    "channels": self._channels,
                }
            )
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def send_audio(self, pcm: bytes) -> None:
        """Send a chunk of raw 16-bit little-endian PCM audio (16 kHz, mono)."""
        if self._ws is not None and not self._ws.closed:
            await self._ws.send_bytes(pcm)

    async def end(self) -> None:
        """Signal end-of-audio; the server flushes and emits ``completed``."""
        if self._ws is not None and not self._ws.closed:
            await self._ws.send_str(json.dumps({"type": "end"}))

    async def close(self) -> None:
        """Close the socket and underlying HTTP session."""
        if self._closed:
            return
        self._closed = True
        if self._ws is not None and not self._ws.closed:
            await self._ws.close()
        if self._session is not None and not self._session.closed:
            await self._session.close()

    def __aiter__(self) -> AsyncIterator[Dict[str, Any]]:
        return self

    async def __anext__(self) -> Dict[str, Any]:
        if self._ws is None or self._ws.closed:
            raise StopAsyncIteration
        msg = await self._ws.receive()
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                return json.loads(msg.data)
            except (ValueError, TypeError):
                raise StopAsyncIteration
        if msg.type == aiohttp.WSMsgType.BINARY:
            # The server never sends binary downstream; skip and keep reading.
            return await self.__anext__()
        # CLOSE / CLOSING / CLOSED / ERROR -> stream is over.
        raise StopAsyncIteration
