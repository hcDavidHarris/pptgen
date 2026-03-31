"""Validator for SourceDocument payloads.

Rules:
    - source_type must be a non-empty string
    - title must be a non-empty string
"""

from __future__ import annotations

from ..ingestion_models import SourceDocument


class SourceValidationError(ValueError):
    """Raised when a SourceDocument fails validation."""


def validate_source(source: SourceDocument) -> None:
    """Validate a SourceDocument.

    Args:
        source: The document to validate.

    Raises:
        SourceValidationError: If any validation rule is violated.
    """
    errors: list[str] = []

    if not source.source_type or not source.source_type.strip():
        errors.append("source_type must be a non-empty string")

    if not source.title or not source.title.strip():
        errors.append("title must be a non-empty string")

    if errors:
        raise SourceValidationError(
            f"SourceDocument validation failed: {'; '.join(errors)}"
        )
