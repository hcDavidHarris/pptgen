"""Validator for BaseBrief payloads.

Rules:
    - topic must be a non-empty string
    - sections must be non-empty
    - provenance must be non-empty
"""

from __future__ import annotations

from ..ingestion_models import BaseBrief


class BriefValidationError(ValueError):
    """Raised when a BaseBrief fails validation."""


def validate_brief(brief: BaseBrief) -> None:
    """Validate a BaseBrief.

    Args:
        brief: The brief to validate.

    Raises:
        BriefValidationError: If any validation rule is violated.
    """
    errors: list[str] = []

    if not brief.topic or not brief.topic.strip():
        errors.append("topic must be a non-empty string")

    if not brief.sections:
        errors.append("sections must be non-empty")

    if not brief.provenance:
        errors.append("provenance must be non-empty")

    if errors:
        raise BriefValidationError(
            f"BaseBrief validation failed: {'; '.join(errors)}"
        )
