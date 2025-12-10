"""
AudioPod SDK Configuration
"""

from dataclasses import dataclass


@dataclass
class ClientConfig:
    """Client configuration settings"""
    base_url: str = "https://api.audiopod.ai"
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    debug: bool = False
    version: str = "1.3.0"

