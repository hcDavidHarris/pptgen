"""Prompt template for transcript insight extraction.

This module owns the prompt text for LLM-driven transcript extraction.
The extractor references this module rather than embedding prompt text
in extraction logic, preserving the prompt-as-configuration discipline.

The prompt is currently unused by the rule-based extractor but is ready
for a future prompt-driven upgrade without touching extractor logic.

Output contract
---------------
The prompt requests a JSON array of insight objects:

    [
      {
        "category": "theme" | "decision" | "action" | "risk" | "priority",
        "text": "<concise insight statement>",
        "confidence": <float 0.0–1.0>,
        "derivation_type": "quoted" | "summarized" | "inferred"
      },
      ...
    ]

Rules enforced via prompt
-------------------------
- 5–15 insights total; prefer fewer, higher-signal insights
- Each insight must be a complete, executive-readable sentence
- Do not repeat the same point across multiple categories
- confidence should reflect how clearly the insight is grounded in the transcript
"""

from __future__ import annotations

EXTRACTION_CATEGORIES = ("theme", "decision", "action", "risk", "priority")

_PROMPT_TEMPLATE = """\
You are an expert at analysing leadership and strategy meeting transcripts.

Given the following transcript, extract the most important insights
across these five categories:

  - theme     : Major strategic or operational themes discussed
  - decision  : Explicit or clearly implied decisions made
  - action    : Action items, next steps, or ownership assignments
  - risk      : Risks, blockers, concerns, or uncertainties raised
  - priority  : Strategic priorities, quarterly rocks, or "must-win" items

Rules:
- Extract 5–15 insights total across all categories.
- Prefer fewer, higher-signal insights over many low-value fragments.
- Each insight must be a single complete sentence suitable for an exec deck.
- Set confidence (0.0–1.0) based on how clearly the transcript supports the insight.
- Use derivation_type "quoted" when the insight is taken almost verbatim,
  "summarized" when it condenses several related statements,
  "inferred" when it is implied but not stated directly.

Respond ONLY with a valid JSON array. No prose, no markdown fences.

Transcript title: {title}

Transcript:
{content}
"""


def get_extraction_prompt(title: str, content: str) -> str:
    """Return the populated transcript extraction prompt.

    Args:
        title:   The meeting or document title.
        content: The full transcript text.

    Returns:
        A ready-to-submit prompt string.
    """
    return _PROMPT_TEMPLATE.format(title=title, content=content)
