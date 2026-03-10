"""
Data models for the Prompt Inspector SDK.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class DetectionResult:
    """
    Represents the result of a prompt injection detection.

    Attributes:
        request_id: Unique identifier for this detection request.
        is_safe: Whether the input text is considered safe.
        score: Risk score (0-1). None when no threat is detected.
        category: List of detected threat categories.
        latency_ms: Server-side processing time in milliseconds.
    """

    request_id: str
    is_safe: bool
    score: Optional[float] = None
    category: List[str] = field(default_factory=list)
    latency_ms: int = 0

    def __repr__(self) -> str:
        status = "SAFE" if self.is_safe else "UNSAFE"
        parts = [f"DetectionResult(status={status}"]
        if self.score is not None:
            parts.append(f"score={self.score}")
        if self.category:
            parts.append(f"category={self.category}")
        parts.append(f"latency={self.latency_ms}ms")
        return ", ".join(parts) + ")"
