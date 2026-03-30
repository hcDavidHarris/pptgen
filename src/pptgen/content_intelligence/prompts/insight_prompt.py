"""Insight prompt definition — Phase 11B.

All insight prompt text lives here.
No prompt strings may appear outside this module.
"""
from __future__ import annotations

_TEMPLATE = """\
Add strategic implications to this presentation slide.

Slide Title: {title}
Core Assertion: {assertion}
Supporting Points:
{supporting_points}

Generate 1 to 3 implications — what this means for the audience, what action \
it demands, or what risk it surfaces. Each must be a complete, specific sentence.

Output ONLY the JSON object. No prose, no code fences, no explanation.
Start with {{ and end with }}.

{{
  "implications": ["string"]
}}
"""


def build_prompt(context: dict) -> str:
    """Build the insight prompt string from context variables.

    Args:
        context: Dict with keys: title, assertion, supporting_points (list).

    Returns:
        Fully rendered prompt string.
    """
    pts: list = context.get("supporting_points") or []
    pts_str = (
        "\n".join(f"- {p}" for p in pts)
        if pts
        else "- (none)"
    )
    return _TEMPLATE.format(
        title=context.get("title") or "",
        assertion=context.get("assertion") or "(none)",
        supporting_points=pts_str,
    )
