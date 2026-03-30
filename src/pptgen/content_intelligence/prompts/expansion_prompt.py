"""Expansion prompt definition — Phase 11B.

All expansion prompt text lives here.
No prompt strings may appear outside this module.
"""
from __future__ import annotations

_TEMPLATE = """\
Expand this presentation slide into structured content.

Slide Title: {title}
Slide Type: {intent_type}
Key Points:
{key_points}
Topic: {topic}{intent_guidance}

Write:
- assertion: one strong, specific sentence — the slide's core claim
- supporting_points: 3 to 5 detailed statements that back the assertion

Output ONLY the JSON object. No prose, no code fences, no explanation.
Start with {{ and end with }}.

{{
  "assertion": "string",
  "supporting_points": ["string", "string", "string"]
}}
"""

# Brief framing hints for slide types where generic output is weakest.
# Injected after the Topic line — empty string for all other intent types.
_INTENT_GUIDANCE: dict[str, str] = {
    "impact": (
        "Focus: quantified business consequences — financial exposure, "
        "compliance risk, customer trust impact, or operational cost."
    ),
    "metrics": (
        "Focus: measurable outcomes — specific numbers, performance benchmarks, "
        "or business KPIs that demonstrate scale or urgency."
    ),
}


def build_prompt(context: dict) -> str:
    """Build the expansion prompt string from context variables.

    Args:
        context: Dict with keys: title, intent_type, key_points (list), topic.

    Returns:
        Fully rendered prompt string.
    """
    key_points: list = context.get("key_points") or []
    kp_str = (
        "\n".join(f"- {p}" for p in key_points)
        if key_points
        else "- (none provided)"
    )
    intent_type: str = context.get("intent_type") or ""
    hint = _INTENT_GUIDANCE.get(intent_type, "")
    intent_guidance = f"\n{hint}" if hint else ""
    return _TEMPLATE.format(
        title=context.get("title") or "",
        intent_type=intent_type,
        key_points=kp_str,
        topic=context.get("topic") or "",
        intent_guidance=intent_guidance,
    )
