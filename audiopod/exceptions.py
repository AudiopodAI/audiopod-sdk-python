"""
AudioPod SDK Exceptions
"""


class AudioPodError(Exception):
    """Base exception for AudioPod SDK"""
    def __init__(self, message, *, status_code=None, detail=None, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after
        self.code = detail.get("code") if isinstance(detail, dict) else None
        self.action = detail.get("action") if isinstance(detail, dict) else None


class AuthenticationError(AudioPodError):
    """Raised when authentication fails"""
    pass


class APIError(AudioPodError):
    """Raised when API returns an error"""
    
    def __init__(self, message: str, status_code: int = None, *, detail=None, retry_after=None):
        super().__init__(message,status_code=status_code,detail=detail,retry_after=retry_after)


class RateLimitError(AudioPodError):
    """Raised when rate limit is exceeded"""
    pass


class ValidationError(AudioPodError):
    """Raised when input validation fails"""
    pass


class InsufficientBalanceError(AudioPodError):
    """Raised when wallet balance is insufficient"""
    
    def __init__(self, message: str, required_cents: int = None, available_cents: int = None, *, detail=None, retry_after=None):
        super().__init__(message,status_code=402,detail=detail,retry_after=retry_after)
        self.required_cents = required_cents
        self.available_cents = available_cents
