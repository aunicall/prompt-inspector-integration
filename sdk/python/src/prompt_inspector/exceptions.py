"""
Custom exception classes for the Prompt Inspector SDK.
"""


class PromptInspectorError(Exception):
    """Base exception for all Prompt Inspector SDK errors."""

    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(PromptInspectorError):
    """Raised when authentication fails (invalid or missing API key)."""

    def __init__(self, message: str = "Authentication failed. Please check your API key."):
        super().__init__(message)


class ValidationError(PromptInspectorError):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Input validation failed."):
        super().__init__(message)


class APIError(PromptInspectorError):
    """Raised when the API returns an error response."""

    def __init__(self, status_code: int, message: str = "API request failed."):
        self.status_code = status_code
        super().__init__(f"[HTTP {status_code}] {message}")


class TimeoutError(PromptInspectorError):
    """Raised when a request exceeds the timeout duration."""

    def __init__(self, timeout: int, message: str = ""):
        if not message:
            message = f"Request timed out after {timeout} seconds."
        super().__init__(message)


class ConnectionError(PromptInspectorError):
    """Raised when a connection to the API server cannot be established."""

    def __init__(self, message: str = "Failed to connect to the Prompt Inspector API server."):
        super().__init__(message)
