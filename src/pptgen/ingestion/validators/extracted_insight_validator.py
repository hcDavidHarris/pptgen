"""Validator for ExtractedInsight payloads.

Rules:
    - text must be non-empty
    - derivation_type must be one of the valid set
"""

from __future__ import annotations

from ..ingestion_models import VALID_DERIVATION_TYPES, ExtractedInsight


class InsightValidationError(ValueError):
    """Raised when an ExtractedInsight fails validation."""


def validate_insight(insight: ExtractedInsight) -> None:
    """Validate a single ExtractedInsight.

    Args:
        insight: The insight to validate.

    Raises:
        InsightValidationError: If any validation rule is violated.
    """
    errors: list[str] = []

    if not insight.text or not insight.text.strip():
        errors.append("text must be a non-empty string")

    if insight.derivation_type not in VALID_DERIVATION_TYPES:
        valid = sorted(VALID_DERIVATION_TYPES)
        errors.append(
            f"derivation_type={insight.derivation_type!r} is not valid; "
            f"must be one of {valid}"
        )

    if errors:
        raise InsightValidationError(
            f"ExtractedInsight validation failed: {'; '.join(errors)}"
        )
