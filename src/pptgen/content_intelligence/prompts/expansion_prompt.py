"""Expansion prompt definition — Phase 11B / 11D.

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
- assertion: one declarative present-tense sentence — the slide's core claim. \
Use "is"/"drives"/"requires"/"costs", never "may"/"can"/"might"/"is associated with".
- supporting_points: 3 to 5 specific statements that substantiate the assertion.

Output ONLY the JSON object. No prose, no code fences, no explanation.
Start with {{ and end with }}.

{{
  "assertion": "string",
  "supporting_points": ["string", "string", "string"]
}}
"""

# Per-intent framing injected after the Topic line.
# Each hint steers content quality for the slide role without hardcoding answers.
_INTENT_GUIDANCE: dict[str, str] = {
    "problem": (
        "Focus: the specific systemic failure — what is breaking, at what scale, "
        "and why it matters now. Convey urgency. Do not propose solutions."
    ),
    "solution": (
        "Focus: concrete prescribed actions — what to do, how it works mechanically, "
        "and what changes as a result. Avoid generic recommendations."
    ),
    "impact": (
        "Focus: quantified business consequences — use ranges not precise figures "
        "(e.g. '$1–5M range', '10–40% increase'). Tie to financial loss, "
        "regulatory risk, or customer churn. Reference industry benchmarks where relevant."
    ),
    "metrics": (
        "Focus: measurable outcomes — use directional ranges or benchmarks "
        "(e.g. 'typically 20–40%'), not fabricated precise numbers. "
        "Ground claims in industry norms or enterprise-scale comparisons."
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
