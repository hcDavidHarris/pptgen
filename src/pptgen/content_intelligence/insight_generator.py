"""Insight generator — Phase 11B.

Prompt-driven insight generation with deterministic fallback.

The public contract is unchanged from Phase 11A:
    generate_insights(EnrichedSlideContent) -> EnrichedSlideContent

Phase 11B behaviour:
    - Attempts prompt-driven insight generation via run_prompt().
    - Falls back to Phase 11A deterministic implication on any failure.
    - Existing fields (title, assertion, supporting_points) are always
      preserved — only implications is updated.
    - No prompt strings live in this module — see prompts/ package.
"""
from __future__ import annotations

import json
from dataclasses import replace as _dc_replace

from .content_models import EnrichedSlideContent
from .guardrails import validate_insight_output
from .prompt_runner import run_prompt

_INSIGHT_PROMPT_NAME = "insight"


def generate_insights(content: EnrichedSlideContent) -> EnrichedSlideContent:
    """Add strategic implications to EnrichedSlideContent.

    Attempts prompt-driven insight generation.  Falls back to a single
    deterministic implication if the prompt fails, returns malformed JSON,
    or produces an empty implications list.

    All existing fields (title, assertion, supporting_points, metadata) are
    always preserved.  Only ``implications`` is updated.

    Args:
        content: Enriched slide content (post-expansion).

    Returns:
        A new EnrichedSlideContent with implications populated and
        ``insights_applied=True`` recorded in metadata.
    """
    context = {
        "title": content.title,
        "assertion": content.assertion or "",
        "supporting_points": list(content.supporting_points),
    }

    def _parse(raw: str) -> EnrichedSlideContent:
        data = json.loads(raw)
        implications = list(data["implications"])
        return EnrichedSlideContent(
            title=content.title,
            assertion=content.assertion,
            supporting_points=content.supporting_points,
            implications=implications,
            metadata={**content.metadata, "insights_applied": True},
            primitive=content.primitive,
        )

    def _validate(result: EnrichedSlideContent) -> bool:
        return validate_insight_output(result)

    _diag_list: list[dict] = []
    result = run_prompt(
        prompt_name=_INSIGHT_PROMPT_NAME,
        context=context,
        parser=_parse,
        fallback=lambda: _generate_insights_fallback(content),
        validator=_validate,
        diagnostics_out=_diag_list,
    )
    # Embed prompt diagnostics in metadata for pipeline-level observability.
    if _diag_list:
        result = _dc_replace(result, metadata={**result.metadata, "_prompt_diag": _diag_list[0]})
    return result


# ---------------------------------------------------------------------------
# Deterministic fallback — identical to Phase 11A
# ---------------------------------------------------------------------------

def _generate_insights_fallback(content: EnrichedSlideContent) -> EnrichedSlideContent:
    """Return Phase 11A deterministic single implication."""
    if content.supporting_points:
        first_point = content.supporting_points[0].rstrip(".")
        implications = [
            f"Given the above, this implies a clear path forward on: {first_point}."
        ]
    else:
        implications = []

    return EnrichedSlideContent(
        title=content.title,
        assertion=content.assertion,
        supporting_points=content.supporting_points,
        implications=implications,
        metadata={**content.metadata, "insights_applied": True},
        primitive=content.primitive,
    )
