"""
AudioPod API Client
"""

import os
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

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
)

logger = logging.getLogger(__name__)


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
            logging.basicConfig(level=logging.DEBUG)

        self.api_key = api_key or os.getenv("AUDIOPOD_API_KEY")
        if not self.api_key:
            raise AuthenticationError(
                "API key required. Pass api_key or set AUDIOPOD_API_KEY environment variable."
            )

        if not self.api_key.startswith("ap_"):
            raise AuthenticationError("Invalid API key format. Keys start with 'ap_'")

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
            "Content-Type": "application/json",
            "User-Agent": f"audiopod-python/{self.config.version}",
            "Accept": "application/json",
        }

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        try:
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status_code == 402:
                try:
                    data = response.json()
                    raise InsufficientBalanceError(
                        data.get("message", "Insufficient balance"),
                        required_cents=data.get("required_cents"),
                        available_cents=data.get("available_cents"),
                    )
                except (ValueError, KeyError):
                    raise InsufficientBalanceError("Insufficient wallet balance")
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
        self.wallet = WalletService(self)

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make API request."""
        url = urljoin(self.config.base_url, endpoint)
        headers = self._get_headers()

        if files:
            headers.pop("Content-Type", None)

        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
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
        self.wallet = WalletService(self, async_mode=True)

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
    ) -> Dict[str, Any]:
        """Make async API request."""
        url = urljoin(self.config.base_url, endpoint)

        async with self.session.request(
            method=method,
            url=url,
            json=json_data,
            data=data,
            params=params,
        ) as response:
            return await self._handle_async_response(response)

    async def _handle_async_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        if response.status == 204:
            return {}
        try:
            response.raise_for_status()
            return await response.json()
        except aiohttp.ClientResponseError as e:
            if response.status == 401:
                raise AuthenticationError("Invalid API key")
            elif response.status == 402:
                try:
                    data = await response.json()
                    raise InsufficientBalanceError(
                        data.get("message", "Insufficient balance"),
                        required_cents=data.get("required_cents"),
                        available_cents=data.get("available_cents"),
                    )
                except:
                    raise InsufficientBalanceError("Insufficient wallet balance")
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

