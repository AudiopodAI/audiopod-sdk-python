"""
AudioPod API Client
"""

import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode, urljoin

import requests
import aiohttp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import ClientConfig
from .exceptions import AuthenticationError, APIError, RateLimitError, InsufficientBalanceError
from .services import (
    VoiceService,
    MusicService,
    TranscriptionService,
    TranslationService,
    SpeakerService,
    DenoiserService,
    CreditService,
    StemExtractionService,
    WalletService,
    VideoService,
    AudiobookService,
    MidiService,
    PodcastService,
    ReaderService,
)

logger = logging.getLogger(__name__)

API_KEYS_URL = "https://audiopod.ai/dashboard/account/api-keys"

AUTH_HINT = f"Set AUDIOPOD_API_KEY (or pass api_key=) — create a key at {API_KEYS_URL}"

BALANCE_HINT = (
    "API-key requests bill your prepaid API wallet (USD). Top it up at "
    f"{API_KEYS_URL} or with client.wallet.create_topup_checkout(amount_cents=...); "
    "check rates with client.wallet.get_pricing()."
)


def _detail_dict(body: Any) -> Dict[str, Any]:
    """The useful part of an error body: FastAPI nests it under ``detail``."""
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, dict):
            return detail
        return body
    return {}


def _server_message(body: Any) -> Optional[str]:
    if isinstance(body, dict):
        detail = body.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, dict) and isinstance(detail.get("message"), str):
            return detail["message"]
        if isinstance(body.get("message"), str):
            return body["message"]
    return None


def _auth_error(body: Any) -> AuthenticationError:
    server = _server_message(body)
    prefix = f"Invalid or missing API key ({server})" if server else "Invalid or missing API key"
    return AuthenticationError(f"{prefix}. {AUTH_HINT}")


def _balance_error(body: Any) -> InsufficientBalanceError:
    info = _detail_dict(body)
    server = _server_message(body) or "Insufficient balance"
    return InsufficientBalanceError(
        f"{server}. {BALANCE_HINT}",
        required_cents=info.get("required_cents"),
        available_cents=info.get("available_cents"),
    )


class BaseClient:
    """Base client with common functionality"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = True,
        debug: bool = False,
    ):
        """
        Initialize the AudioPod API client.

        Args:
            api_key: Your AudioPod API key. If None, reads from AUDIOPOD_API_KEY env var.
            base_url: API base URL. Defaults to https://api.audiopod.ai
            timeout: Request timeout in seconds.
            max_retries: Maximum retries for failed requests.
            verify_ssl: Whether to verify SSL certificates.
            debug: Enable debug logging.
        """
        if debug:
            # Security audit F8: scope debug logging to the "audiopod" logger
            # instead of the root logger, and hold the HTTP transport libraries
            # (which can echo the Authorization / X-API-Key request headers) at
            # WARNING. Previously `logging.basicConfig(level=DEBUG)` turned on
            # root DEBUG for the whole host application, which could surface the
            # API key via urllib3 / http.client wire logs.
            logging.getLogger("audiopod").setLevel(logging.DEBUG)
            if not logging.getLogger().handlers:
                logging.basicConfig(level=logging.INFO)
            for _noisy in ("urllib3", "requests", "http.client", "aiohttp"):
                logging.getLogger(_noisy).setLevel(logging.WARNING)

        self.api_key = api_key or os.getenv("AUDIOPOD_API_KEY")
        if not self.api_key:
            raise AuthenticationError(f"API key required. {AUTH_HINT}")

        if not self.api_key.startswith("ap_"):
            raise AuthenticationError(
                f"Invalid API key format: AudioPod keys start with 'ap_'. {AUTH_HINT}"
            )

        self.config = ClientConfig(
            base_url=base_url or "https://api.audiopod.ai",
            timeout=timeout,
            max_retries=max_retries,
            verify_ssl=verify_ssl,
            debug=debug,
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": f"audiopod-python/{self.config.version}",
            "Accept": "application/json",
        }

    @staticmethod
    def _json_or_none(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return None

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise _auth_error(self._json_or_none(response))
            elif response.status_code == 402:
                raise _balance_error(self._json_or_none(response))
            elif response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                try:
                    error_data = response.json()
                    message = error_data.get("detail", str(e))
                except:
                    message = str(e)
                raise APIError(f"API error: {message}", status_code=response.status_code)


class Client(BaseClient):
    """
    Synchronous AudioPod API Client.

    Example:
        ```python
        from audiopod import Client

        client = Client(api_key="ap_your_key")

        # Check wallet balance
        balance = client.wallet.get_balance()
        print(f"Balance: {balance['balance_usd']}")

        # Extract stems
        job = client.stem_extraction.extract_stems(
            audio_file="song.mp3",
            stem_types=["vocals", "drums", "bass", "other"]
        )
        ```
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.config.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "DELETE"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Services
        self.voice = VoiceService(self)
        self.music = MusicService(self)
        self.transcription = TranscriptionService(self)
        self.translation = TranslationService(self)
        self.speaker = SpeakerService(self)
        self.denoiser = DenoiserService(self)
        self.credits = CreditService(self)
        self.stem_extraction = StemExtractionService(self)
        self.stems = self.stem_extraction  # Alias for consistency with Node.js SDK
        self.wallet = WalletService(self)
        self.video = VideoService(self)
        self.audiobook = AudiobookService(self)
        self.midi = MidiService(self)
        self.podcast = PodcastService(self)
        self.reader = ReaderService(self)

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make API request."""
        url = urljoin(self.config.base_url, endpoint)
        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        if files or (data is not None and json_data is None):
            # Form posts (multipart or urlencoded): let requests set the
            # Content-Type. The JSON default would make the server ignore
            # every form field (a URL-only denoise or a TTS request lost its
            # fields this way).
            request_headers.pop("Content-Type", None)

        response = self.session.request(
            method=method,
            url=url,
            headers=request_headers,
            data=data,
            json=json_data,
            files=files,
            params=params,
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )
        return self._handle_response(response)

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        return self.request("GET", "/api/v1/auth/me")

    def close(self):
        """Close client session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AsyncClient(BaseClient):
    """
    Asynchronous AudioPod API Client.

    Example:
        ```python
        import asyncio
        from audiopod import AsyncClient

        async def main():
            async with AsyncClient(api_key="ap_your_key") as client:
                balance = await client.wallet.get_balance()
                print(f"Balance: {balance['balance_usd']}")

        asyncio.run(main())
        ```
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._session: Optional[aiohttp.ClientSession] = None

        # Services
        self.voice = VoiceService(self, async_mode=True)
        self.music = MusicService(self, async_mode=True)
        self.transcription = TranscriptionService(self, async_mode=True)
        self.translation = TranslationService(self, async_mode=True)
        self.speaker = SpeakerService(self, async_mode=True)
        self.denoiser = DenoiserService(self, async_mode=True)
        self.credits = CreditService(self, async_mode=True)
        self.stem_extraction = StemExtractionService(self, async_mode=True)
        self.stems = self.stem_extraction  # Alias for consistency with Node.js SDK
        self.wallet = WalletService(self, async_mode=True)
        self.video = VideoService(self, async_mode=True)
        self.audiobook = AudiobookService(self, async_mode=True)
        self.midi = MidiService(self, async_mode=True)
        self.podcast = PodcastService(self, async_mode=True)
        self.reader = ReaderService(self, async_mode=True)

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl)
            self._session = aiohttp.ClientSession(
                timeout=timeout, connector=connector, headers=self._get_headers()
            )
        return self._session

    async def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make async API request."""
        url = urljoin(self.config.base_url, endpoint)

        if files:
            # aiohttp has no requests-style ``files=``; build a multipart body via
            # FormData. The session default header is Content-Type: application/json,
            # so we must override it per-request with the multipart content type
            # (including the generated boundary) — otherwise the body is sent as
            # JSON and the uploaded binary is silently dropped.
            form = aiohttp.FormData()
            for key, value in (data or {}).items():
                if value is None:
                    continue
                form.add_field(key, str(value))
            for field, spec in files.items():
                if isinstance(spec, (tuple, list)):
                    filename = spec[0]
                    content = spec[1]
                    content_type = spec[2] if len(spec) > 2 else None
                    form.add_field(
                        field, content, filename=filename, content_type=content_type
                    )
                else:
                    form.add_field(field, spec)
            payload = form()
            async with self.session.request(
                method=method,
                url=url,
                data=payload,
                params=params,
                headers={**(headers or {}), "Content-Type": payload.content_type},
            ) as response:
                return await self._handle_async_response(response)

        if data is not None and json_data is None:
            # A form post without files: urlencode it and override the
            # session's JSON Content-Type, or the server ignores the fields.
            # Same encoding as requests: lists repeat the key, None is dropped.
            form_fields = [
                (key, str(item))
                for key, value in data.items()
                if value is not None
                for item in (value if isinstance(value, (list, tuple)) else [value])
            ]
            async with self.session.request(
                method=method,
                url=url,
                data=urlencode(form_fields),
                params=params,
                headers={
                    **(headers or {}),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as response:
                return await self._handle_async_response(response)

        async with self.session.request(
            method=method,
            url=url,
            json=json_data,
            data=data,
            params=params,
            headers=headers,
        ) as response:
            return await self._handle_async_response(response)

    async def _handle_async_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        if response.status == 204:
            return {}
        try:
            response.raise_for_status()
            return await response.json()
        except aiohttp.ClientResponseError as e:
            if response.status in (401, 402):
                try:
                    body = await response.json(content_type=None)
                except Exception:
                    body = None
                if response.status == 401:
                    raise _auth_error(body)
                raise _balance_error(body)
            elif response.status == 429:
                raise RateLimitError("Rate limit exceeded")
            else:
                raise APIError(f"API error: {e}", status_code=response.status)

    async def get_user_info(self) -> Dict[str, Any]:
        """Get current user information."""
        return await self.request("GET", "/api/v1/auth/me")

    async def close(self):
        """Close async client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

