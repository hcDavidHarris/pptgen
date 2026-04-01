"""Content intelligence guardrails — Phase 11B.

Lightweight, pure validation helpers for prompt output types.
Each function returns ``True`` if the value is structurally valid for use
downstream; ``False`` otherwise.

Rules
-----
validate_slide_intent
    - title must be a non-empty, non-blank string
    - intent_type must be a non-empty, non-blank string
    - key_points must have at least 1 item

validate_enriched_content
    - assertion must be a non-empty, non-blank string
    - supporting_points must have at least 3 items

validate_insight_output
    - implications must be a non-empty list (at least 1 item)

Design
------
- Pure functions, no side effects.
- No logging, no raising — always return bool.
- Called by prompt_runner.run_prompt() as the *validator* argument.
"""
from __future__ import annotations

from .content_models import EnrichedSlideContent, SlideIntent

_MIN_KEY_POINTS: int = 1
_MIN_SUPPORTING_POINTS: int = 3
_MIN_IMPLICATIONS: int = 1


def validate_slide_intent(slide: SlideIntent) -> bool:
    """Return True if *slide* satisfies narrative output requirements.

    Requirements:
        - ``title``: non-empty, non-blank string.
        - ``intent_type``: non-empty, non-blank string.
        - ``key_points``: at least 1 item.

    Args:
        slide: The SlideIntent to validate.

    Returns:
        True if valid; False otherwise.
    """
    if not isinstance(slide, SlideIntent):
        return False
    if not slide.title or not slide.title.strip():
        return False
    if not slide.intent_type or not slide.intent_type.strip():
        return False
    if not slide.key_points or len(slide.key_points) < _MIN_KEY_POINTS:
        return False
    return True


def validate_enriched_content(content: EnrichedSlideContent) -> bool:
    """Return True if *content* satisfies expansion output requirements.

    Requirements:
        - ``assertion``: non-empty, non-blank string.
        - ``supporting_points``: at least 3 items.

    Args:
        content: The EnrichedSlideContent to validate.

    Returns:
        True if valid; False otherwise.
    """
    if not isinstance(content, EnrichedSlideContent):
        return False
    if not content.assertion or not content.assertion.strip():
        return False
    if len(content.supporting_points) < _MIN_SUPPORTING_POINTS:
        return False
    return True


def validate_insight_output(content: EnrichedSlideContent) -> bool:
    """Return True if *content* satisfies insight output requirements.

    Requirements:
        - ``implications``: non-None list with at least 1 item.

    Args:
        content: The EnrichedSlideContent to validate.

    Returns:
        True if valid; False otherwise.
    """
    if not isinstance(content, EnrichedSlideContent):
        return False
    if not content.implications or len(content.implications) < _MIN_IMPLICATIONS:
        return False
    return True
