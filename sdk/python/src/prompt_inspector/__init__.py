"""
Prompt Inspector Python SDK

A lightweight client for the Prompt Inspector AI prompt injection detection service.
"""

from .client import PromptInspector
from .exceptions import (
    PromptInspectorError,
    AuthenticationError,
    ValidationError,
    APIError,
    TimeoutError,
    ConnectionError,
)
from .models import DetectionResult

__all__ = [
    "PromptInspector",
    "DetectionResult",
    "PromptInspectorError",
    "AuthenticationError",
    "ValidationError",
    "APIError",
    "TimeoutError",
    "ConnectionError",
]

__version__ = "0.1.0"
