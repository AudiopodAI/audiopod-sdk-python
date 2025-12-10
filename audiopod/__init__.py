"""
AudioPod SDK for Python
Professional Audio Processing powered by AI
"""

__version__ = "1.3.0"

from .client import Client, AsyncClient
from .exceptions import (
    AudioPodError,
    AuthenticationError,
    APIError,
    RateLimitError,
    ValidationError,
    InsufficientBalanceError,
)

__all__ = [
    "Client",
    "AsyncClient",
    "AudioPodError",
    "AuthenticationError", 
    "APIError",
    "RateLimitError",
    "ValidationError",
    "InsufficientBalanceError",
    "__version__",
]

