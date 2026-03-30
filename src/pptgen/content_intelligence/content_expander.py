"""Content expander — Phase 11B / 11C.

Prompt-driven slide expansion with deterministic fallback.

The public contract is unchanged from Phase 11A:
    expand_slide(SlideIntent) -> EnrichedSlideContent

Phase 11B behaviour:
    - Attempts prompt-driven expansion via run_prompt().
    - Falls back to Phase 11A deterministic expansion on any failure.
    - Partial prompt output is NEVER merged with fallback — all-or-nothing.
    - No prompt strings live in this module — see prompts/ package.

Phase 11C addition:
    - slide.primitive is propagated to EnrichedSlideContent.primitive.
    - primitive is also recorded in metadata for observability.
"""
from __future__ import annotations

import json
from dataclasses import replace as _dc_replace

from .content_models import EnrichedSlideContent, SlideIntent
from .guardrails import validate_enriched_content
from .prompt_runner import run_prompt

_EXPANSION_PROMPT_NAME = "expansion"
_MIN_SUPPORTING_POINTS = 3


def expand_slide(slide: SlideIntent) -> EnrichedSlideContent:
    """Expand a SlideIntent into EnrichedSlideContent.

    Attempts prompt-driven expansion.  Falls back to deterministic logic if
    the prompt fails, returns malformed JSON, or produces content with fewer
    than 3 supporting points or an empty assertion.

    Partial prompt output is never merged with fallback content; the result
    is always entirely from the prompt or entirely from the fallback.

    Args:
        slide: The slide intent to expand.

    Returns:
        EnrichedSlideContent with a non-empty assertion and >= 3 supporting
        points.
    """
    context = {
        "title": slide.title,
        "intent_type": slide.intent_type,
        "key_points": list(slide.key_points),
        "topic": slide.title,
    }

    def _parse(raw: str) -> EnrichedSlideContent:
        data = json.loads(raw)
        return EnrichedSlideContent(
            title=slide.title,
            assertion=data["assertion"],
            supporting_points=list(data["supporting_points"]),
            metadata={
                "intent_type": slide.intent_type,
                "primitive": slide.primitive,
                "source": "prompt",
            },
            primitive=slide.primitive,
        )

    def _validate(content: EnrichedSlideContent) -> bool:
        return validate_enriched_content(content)

    _diag_list: list[dict] = []
    result = run_prompt(
        prompt_name=_EXPANSION_PROMPT_NAME,
        context=context,
        parser=_parse,
        fallback=lambda: _expand_slide_fallback(slide),
        validator=_validate,
        diagnostics_out=_diag_list,
    )
    # Embed prompt diagnostics in metadata for pipeline-level observability.
    # "_prompt_diag" records whether the LLM path ran and why fallback fired.
    if _diag_list:
        result = _dc_replace(result, metadata={**result.metadata, "_prompt_diag": _diag_list[0]})
    return result


# ---------------------------------------------------------------------------
# Deterministic fallback — identical to Phase 11A
# ---------------------------------------------------------------------------

def _expand_slide_fallback(slide: SlideIntent) -> EnrichedSlideContent:
    """Return Phase 11A deterministic expansion."""
    assertion = f"{slide.title}."
    supporting_points = list(slide.key_points)
    while len(supporting_points) < _MIN_SUPPORTING_POINTS:
        idx = len(supporting_points) + 1
        supporting_points.append(
            f"Supporting detail {idx} for {slide.intent_type}."
        )
    return EnrichedSlideContent(
        title=slide.title,
        assertion=assertion,
        supporting_points=supporting_points,
        metadata={
            "intent_type": slide.intent_type,
            "primitive": slide.primitive,
            "source": "content_expander",
        },
        primitive=slide.primitive,
    )
