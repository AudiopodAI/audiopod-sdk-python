"""
AudioPod SDK for Python
Professional Audio Processing powered by AI
"""

__version__ = "2.6.0"

from .client import Client, AsyncClient
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
]

