"""Confidence classification helpers for dead-library findings."""

from .models import ConfidenceLevel


def classify_confidence(score: float) -> ConfidenceLevel:
    """Map a normalized score to a stable confidence level.

    Args:
        score: Value from 0.0 through 1.0.

    Raises:
        ValueError: If *score* lies outside the normalized interval.
    """

    if not 0.0 <= score <= 1.0:
        raise ValueError("confidence score must be between 0.0 and 1.0")
    if score >= 0.8:
        return ConfidenceLevel.HIGH
    if score >= 0.4:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW
