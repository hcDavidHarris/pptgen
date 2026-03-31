"""Narrative prompt definition — Phase 11B.

All narrative prompt text lives here.
No prompt strings may appear outside this module.
"""
from __future__ import annotations

_TEMPLATE = """\
Generate a slide narrative for a business presentation.

Topic: {topic}
Goal: {goal}
Audience: {audience}

Produce 3 to 5 slides that tell a logical story arc: establish the problem first, \
then evidence or solution, then business impact.
Each slide must have:
- title: concise, specific, references the topic
- intent_type: one of "problem", "solution", "impact", "metrics", "context", "recommendation"
- key_points: 2 to 4 specific claims — not topic labels, not vague phrases

Output ONLY the JSON array. No prose, no code fences, no explanation.
Start with [ and end with ].

[
  {{
    "title": "string",
    "intent_type": "string",
    "key_points": ["string", "string"]
  }}
]
"""


def build_prompt(context: dict) -> str:
    """Build the narrative prompt string from context variables.

    Args:
        context: Dict with keys: topic, goal, audience.

    Returns:
        Fully rendered prompt string.
    """
    return _TEMPLATE.format(
        topic=context.get("topic") or "the topic",
        goal=context.get("goal") or "Not specified",
        audience=context.get("audience") or "General audience",
    )
