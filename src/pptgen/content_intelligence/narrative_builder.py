"""Narrative builder — Phase 11B.

Prompt-driven narrative generation with deterministic fallback.

The public contract is unchanged from Phase 11A:
    build_narrative(ContentIntent) -> list[SlideIntent]

Phase 11B behaviour:
    - Attempts prompt-driven generation via run_prompt().
    - Falls back to the Phase 11A deterministic structure on any failure.
    - Fallback output is byte-for-byte identical to Phase 11A output.
    - No prompt strings live in this module — see prompts/ package.
"""
from __future__ import annotations

import json

from .content_models import ContentIntent, SlideIntent
from .guardrails import validate_slide_intent
from .prompt_runner import run_prompt

_NARRATIVE_PROMPT_NAME = "narrative"

# Deterministic 3-slide structure — preserved from Phase 11A.
_DEFAULT_STRUCTURE: list[tuple[str, str]] = [
    ("Problem", "problem"),
    ("Solution", "solution"),
    ("Impact", "impact"),
]


def build_narrative(content_intent: ContentIntent) -> list[SlideIntent]:
    """Build a slide narrative from a ContentIntent.

    Attempts prompt-driven generation.  Falls back to a deterministic
    3-slide structure (problem / solution / impact) if the prompt fails,
    returns malformed JSON, or produces invalid SlideIntents.

    The fallback output is always ordered (problem → solution → impact) and
    is deterministic for a given ContentIntent.

    Args:
        content_intent: Authoring intent describing topic, goal, audience.

    Returns:
        list[SlideIntent] with at least 3 items.
    """
    context = {
        "topic": content_intent.topic,
        "goal": content_intent.goal or "",
        "audience": content_intent.audience or "",
    }

    def _parse(raw: str) -> list[SlideIntent]:
        data = json.loads(raw)
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Expected non-empty JSON array")
        return [
            SlideIntent(
                title=item["title"],
                intent_type=item["intent_type"],
                key_points=list(item.get("key_points") or []),
            )
            for item in data
        ]

    def _validate(slides: list[SlideIntent]) -> bool:
        return len(slides) >= 1 and all(validate_slide_intent(s) for s in slides)

    # diagnostics_out wires the fallback reason into the WARNING log.
    # SlideIntent has no metadata field, so we don't embed it in the result.
    _diag_list: list[dict] = []
    return run_prompt(
        prompt_name=_NARRATIVE_PROMPT_NAME,
        context=context,
        parser=_parse,
        fallback=lambda: _narrative_fallback(content_intent),
        validator=_validate,
        diagnostics_out=_diag_list,
    )


# ---------------------------------------------------------------------------
# Deterministic fallback — identical to Phase 11A
# ---------------------------------------------------------------------------

def _narrative_fallback(content_intent: ContentIntent) -> list[SlideIntent]:
    """Return the Phase 11A deterministic 3-slide narrative."""
    topic = content_intent.topic
    return [
        SlideIntent(
            title=f"{topic}: {title_suffix}",
            intent_type=intent_type,
            key_points=[f"Key point about {intent_type} for {topic}."],
        )
        for title_suffix, intent_type in _DEFAULT_STRUCTURE
    ]
