"""
AudioPod SDK for Python
Professional Audio Processing powered by AI
"""

from ._version import VERSION as __version__

from .client import Client, AsyncClient
from .workflow_contracts import VOICE_CONSENT_VERSION
from . import workflow_contracts
from .exceptions import (
    AudioPodError,
    AuthenticationError,
    APIError,
    RateLimitError,
    ValidationError,
    InsufficientBalanceError,
)

# Alias for consistency with documentation and Node.js SDK
AudioPod = Client

__all__ = [
    "Client",
    "AsyncClient",
    "AudioPod",  # Alias for Client
    "AudioPodError",
    "AuthenticationError", 
    "APIError",
    "RateLimitError",
    "ValidationError",
    "InsufficientBalanceError",
    "__version__",
    "VOICE_CONSENT_VERSION",
    "workflow_contracts",
]
