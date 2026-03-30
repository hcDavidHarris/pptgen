"""Slide critic — Phase 11A.

Enforces minimum content quality rules on EnrichedSlideContent.
Auto-corrects rather than raising errors — governance enforcement
(hard failures) lives in the existing governance layer.
"""

from __future__ import annotations

from .content_models import EnrichedSlideContent

_MIN_SUPPORTING_POINTS = 3


def critique_slide(content: EnrichedSlideContent) -> EnrichedSlideContent:
    """Enforce minimum quality rules on enriched slide content.

    Rules:
        - assertion must be non-empty (auto-fills from title if missing).
        - supporting_points must have >= 3 items (auto-expands if needed).

    Args:
        content: The enriched slide to critique.

    Returns:
        A new EnrichedSlideContent that satisfies all quality rules, with
        ``critic_applied=True`` recorded in metadata.
    """
    assertion = content.assertion or f"{content.title}."

    supporting_points = list(content.supporting_points)
    while len(supporting_points) < _MIN_SUPPORTING_POINTS:
        idx = len(supporting_points) + 1
        supporting_points.append(f"Additional supporting point {idx}.")

    return EnrichedSlideContent(
        title=content.title,
        assertion=assertion,
        supporting_points=supporting_points,
        implications=content.implications,
        metadata={**content.metadata, "critic_applied": True},
        primitive=content.primitive,
    )
