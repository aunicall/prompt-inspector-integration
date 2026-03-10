"""
Prompt Inspector SDK client.

Provides the main PromptInspector class for interacting with the
Prompt Inspector API detection service.
"""

import os
from typing import Optional

import httpx

from .exceptions import (
    AuthenticationError,
    ValidationError,
    APIError,
    TimeoutError,
    ConnectionError,
)
from .models import DetectionResult

# Default API base URL
DEFAULT_BASE_URL = "https://promptinspector.io"
DEFAULT_TIMEOUT = 30  # seconds


class PromptInspector:
    """
    Client for the Prompt Inspector prompt injection detection service.

    Usage::

        from prompt_inspector import PromptInspector

        client = PromptInspector(api_key="your-api-key")
        result = client.detect("some user input text")
        print(result.is_safe)
        client.close()

    Or as a context manager::

        with PromptInspector(api_key="your-api-key") as client:
            result = client.detect("some user input text")
            print(result.is_safe)

    Args:
        api_key: The API key for authentication. If not provided,
                 the SDK will attempt to read from the PMTINSP_API_KEY
                 environment variable.
        base_url: The base URL of the Prompt Inspector API server.
                  Defaults to https://promptinspector.io.
        timeout: Default request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        # Resolve API key: explicit param > env var
        resolved_key = api_key
        if not resolved_key:
            resolved_key = os.environ.get("PMTINSP_API_KEY")
        if not resolved_key:
            raise AuthenticationError(
                "API key is required. Provide it via the 'api_key' parameter "
                "or set the PMTINSP_API_KEY environment variable."
            )

        self._api_key = resolved_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._closed = False

        # Build the detection endpoint URL
        self._detect_url = f"{self._base_url}/api/v1/detect/sdk"

        # Create HTTP client with persistent connection pool
        self._http = httpx.Client(
            headers={"X-App-Key": self._api_key},
            timeout=httpx.Timeout(self._timeout),
        )

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "PromptInspector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, text: str, *, timeout: Optional[int] = None) -> DetectionResult:
        """
        Detect potential prompt injection in the given text.

        Args:
            text: The text to analyse (required, non-empty string).
            timeout: Request timeout in seconds. Overrides the default
                     timeout set during initialisation.

        Returns:
            A DetectionResult containing the analysis outcome.

        Raises:
            ValidationError: If the input text is invalid.
            AuthenticationError: If the API key is rejected.
            APIError: If the API returns an error response.
            TimeoutError: If the request exceeds the timeout.
            ConnectionError: If a connection cannot be established.
        """
        self._ensure_open()

        # Validate input
        if not isinstance(text, str) or not text.strip():
            raise ValidationError("Parameter 'text' is required and must be a non-empty string.")

        request_timeout = timeout if timeout is not None else self._timeout

        try:
            response = self._http.post(
                self._detect_url,
                json={"input_text": text},
                timeout=httpx.Timeout(request_timeout),
            )
        except httpx.TimeoutException:
            raise TimeoutError(request_timeout)
        except httpx.ConnectError:
            raise ConnectionError(
                f"Failed to connect to the Prompt Inspector API at {self._base_url}. "
                "Please check the base_url and your network connection."
            )
        except httpx.HTTPError as exc:
            raise ConnectionError(f"HTTP error occurred: {exc}")

        return self._handle_response(response)

    def close(self) -> None:
        """
        Close the SDK client and release all associated resources.

        After calling close(), the client instance can no longer be used
        for detection requests.
        """
        if not self._closed:
            self._http.close()
            self._closed = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_open(self) -> None:
        """Raise an error if the client has already been closed."""
        if self._closed:
            raise PromptInspectorError(
                "This PromptInspector client has been closed. "
                "Create a new instance to continue making requests."
            )

    def _handle_response(self, response: httpx.Response) -> DetectionResult:
        """Parse an API response into a DetectionResult or raise an appropriate error."""
        if response.status_code == 200:
            data = response.json()
            result = data.get("result", {})
            return DetectionResult(
                request_id=data.get("request_id", ""),
                is_safe=result.get("is_safe", True),
                score=result.get("score"),
                category=result.get("category", []),
                latency_ms=data.get("latency_ms", 0),
            )

        # Handle known error codes
        if response.status_code == 401 or response.status_code == 403:
            raise AuthenticationError(
                "Authentication failed. Please verify your API key and app_id."
            )

        if response.status_code == 413:
            raise ValidationError(
                "The input text exceeds the maximum allowed length for your plan."
            )

        if response.status_code == 422:
            detail = ""
            try:
                body = response.json()
                detail = str(body.get("detail", ""))
            except Exception:
                pass
            raise ValidationError(f"Invalid request parameters. {detail}".strip())

        if response.status_code == 429:
            raise APIError(
                status_code=429,
                message="Rate limit exceeded. Please reduce your request frequency.",
            )

        # Generic API error
        detail = ""
        try:
            body = response.json()
            detail = str(body.get("detail", ""))
        except Exception:
            detail = response.text[:200] if response.text else ""

        raise APIError(
            status_code=response.status_code,
            message=detail or f"Unexpected error (HTTP {response.status_code}).",
        )


# Import here to avoid circular import at module level
from .exceptions import PromptInspectorError  # noqa: E402
