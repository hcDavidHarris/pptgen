"""Primitive-aware content validator — Phase 11C.

Validates EnrichedSlideContent against its assigned semantic primitive's
content-depth requirements.  This is strictly stronger than the generic
guardrail checks: each primitive enforces its own reasoning pattern.

Rules applied per primitive:
    All primitives:
        - assertion must be a non-empty, non-blank string
        - supporting_points count >= primitive.minimum_supporting_points

    Primitives that require_implications (problem_statement, metrics_with_insight,
    recommendation):
        - implications must be non-None with count >= primitive.minimum_implications

Design:
- Pure functions, no side effects.
- Returns PrimitiveValidationResult — never raises.
- Tolerates unknown primitive names by falling back to fallback primitive rules.
- Violations are explicit strings that describe what is missing.

Public API:
    validate_primitive_content(content, primitive_name) -> PrimitiveValidationResult
    PrimitiveValidationResult
"""

from __future__ import annotations

from dataclasses import dataclass

from .content_models import EnrichedSlideContent
from .primitive_registry import FALLBACK_PRIMITIVE_NAME, get_primitive


@dataclass(frozen=True)
class PrimitiveValidationResult:
    """Outcome of a primitive-aware content validation check.

    Attributes:
        passed: True if all primitive rules are satisfied.
        primitive_name: The primitive whose rules were applied.
        violations: Tuple of human-readable violation descriptions.
            Empty when passed is True.
    """

    passed: bool
    primitive_name: str
    violations: tuple[str, ...]


def validate_primitive_content(
    content: EnrichedSlideContent,
    primitive_name: str,
) -> PrimitiveValidationResult:
    """Validate *content* against the rules of *primitive_name*.

    Applies primitive-specific minimum content depth requirements.
    An unknown *primitive_name* is treated as the fallback primitive.

    Args:
        content: The enriched slide content to validate.
        primitive_name: The semantic primitive to validate against.

    Returns:
        PrimitiveValidationResult with passed=True and empty violations
        on success, or passed=False with a non-empty violations tuple.
    """
    # Resolve primitive definition; fall back gracefully on unknown names.
    try:
        prim = get_primitive(primitive_name)
    except KeyError:
        prim = get_primitive(FALLBACK_PRIMITIVE_NAME)
        primitive_name = FALLBACK_PRIMITIVE_NAME

    violations: list[str] = []

    # Rule 1 — assertion must be a non-empty, non-blank string.
    if not content.assertion or not content.assertion.strip():
        violations.append(
            f"[{primitive_name}] assertion is missing or blank"
        )

    # Rule 2 — supporting_points count must meet the primitive minimum.
    actual_points = len(content.supporting_points)
    required_points = prim.minimum_supporting_points
    if actual_points < required_points:
        violations.append(
            f"[{primitive_name}] requires at least {required_points} supporting points, "
            f"found {actual_points}"
        )

    # Rule 3 — implications required by this primitive.
    if prim.requires_implications:
        actual_implications = len(content.implications) if content.implications else 0
        required_implications = prim.minimum_implications
        if actual_implications < required_implications:
            violations.append(
                f"[{primitive_name}] requires at least {required_implications} implication(s), "
                f"found {actual_implications}"
            )

    passed = len(violations) == 0
    return PrimitiveValidationResult(
        passed=passed,
        primitive_name=primitive_name,
        violations=tuple(violations),
    )
