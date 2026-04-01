"""Retry policy for job execution failures."""

from __future__ import annotations


def is_retryable(error_category: str) -> bool:
    """Return True if the error category is eligible for retry.

    Only transient errors (AI provider failures, unexpected system errors)
    are retried. Validation and configuration errors are terminal — retrying
    would produce the same outcome.
    """
    return error_category in ("ai_provider", "system")


def get_backoff_seconds(retry_count: int) -> float:
    """Exponential backoff capped at 60 seconds.

    retry_count=0 -> 1s, retry_count=1 -> 2s, retry_count=2 -> 4s,
    retry_count=3 -> 8s, ..., retry_count>=6 -> 60s
    """
    return min(2 ** retry_count, 60)
