"""
AudioPod SDK Exceptions
"""


class AudioPodError(Exception):
    """Base exception for AudioPod SDK"""
    pass


class AuthenticationError(AudioPodError):
    """Raised when authentication fails"""
    pass


class APIError(AudioPodError):
    """Raised when API returns an error"""
    
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(AudioPodError):
    """Raised when rate limit is exceeded"""
    pass


class ValidationError(AudioPodError):
    """Raised when input validation fails"""
    pass


class InsufficientBalanceError(AudioPodError):
    """Raised when wallet balance is insufficient"""
    
    def __init__(self, message: str, required_cents: int = None, available_cents: int = None):
        super().__init__(message)
        self.required_cents = required_cents
        self.available_cents = available_cents

