"""Real extractor for Zoom / meeting transcript sources (Phase 12B).

Replaces the stub extractor for source_type="zoom_transcript".

Approach
--------
Rule-based signal extraction: deterministic, no LLM dependency.
Each sentence (or paragraph chunk) is scored against five category
signal banks.  The highest-scoring sentences per category are returned
as ExtractedInsight objects, capped to produce a concise 5–15 insight
set suitable for an executive summary deck.

This extractor is designed for correctness and observability over recall.
It prefers fewer, high-confidence insights over exhaustive enumeration.

Categories extracted
--------------------
    theme     — strategic or operational themes discussed
    decision  — explicit or implied decisions made
    action    — action items, next steps, ownership assignments
    risk      — risks, blockers, concerns, or uncertainties
    priority  — priorities, rocks, critical focus areas

Provenance
----------
- Insights drawn directly from identifiable sentences use derivation_type "quoted"
  with a source_pointer referencing the sentence index.
- Thematic summaries aggregated across multiple statements use "summarized".
- Confidence is set per-category based on signal density.

Prompt module reference
-----------------------
The companion prompt template lives at:
    pptgen.ingestion.prompts.transcript_extraction_prompt

It is available for a future LLM-backed upgrade without changing this
module's public interface.
"""

from __future__ import annotations

import re
from typing import Any

from ..ingestion_models import ExtractedInsight, SourceDocument

# ---------------------------------------------------------------------------
# Signal banks — each is a tuple of lowercase keyword/phrase signals
# ---------------------------------------------------------------------------

_THEME_SIGNALS: tuple[str, ...] = (
    "strategy", "strategic", "vision", "mission", "objective", "goal",
    "initiative", "focus", "direction", "approach", "roadmap", "transformation",
    "growth", "innovation", "platform", "capability", "value", "opportunity",
    "alignment", "culture", "north star", "positioning",
)

_DECISION_SIGNALS: tuple[str, ...] = (
    "decided", "decision", "agreed", "agree", "approved", "approve",
    "resolved", "confirmed", "confirm", "going forward", "we will",
    "we are", "conclusion", "voted", "commit", "committed",
    "will proceed", "move forward", "signed off", "green light",
)

_ACTION_SIGNALS: tuple[str, ...] = (
    "action item", "follow up", "follow-up", "owner", "owners",
    "responsible", "will do", "will create", "will build", "will deliver",
    "needs to", "need to", "must", "should", "by next", "deadline",
    "assigned", "assign", "take", "handle", "ensure", "create",
    "build", "implement", "deliver", "complete", "schedule", "prepare",
    "reach out", "coordinate", "review", "present", "share",
)

_RISK_SIGNALS: tuple[str, ...] = (
    "risk", "concern", "blocker", "blocking", "challenge", "issue",
    "problem", "obstacle", "worry", "worried", "threat", "uncertain",
    "unclear", "dependency", "dependencies", "vulnerable", "exposure",
    "gap", "constraint", "bottleneck", "delay", "behind", "miss",
    "missing", "lack", "shortage", "capacity",
)

_PRIORITY_SIGNALS: tuple[str, ...] = (
    "priority", "priorities", "rock", "rocks", "quarter", "quarterly",
    "q1", "q2", "q3", "q4", "critical", "urgent", "top", "most important",
    "key", "essential", "must-have", "must have", "number one",
    "focus area", "this quarter", "fy", "okr", "kpi",
)

# Category config: (signals, max_insights, base_confidence, derivation_type)
_CATEGORY_CONFIG: dict[str, tuple[tuple[str, ...], int, float, str]] = {
    "theme":    (_THEME_SIGNALS,    3, 0.70, "summarized"),
    "decision": (_DECISION_SIGNALS, 3, 0.85, "quoted"),
    "action":   (_ACTION_SIGNALS,   3, 0.80, "quoted"),
    "risk":     (_RISK_SIGNALS,     3, 0.75, "quoted"),
    "priority": (_PRIORITY_SIGNALS, 3, 0.80, "summarized"),
}

# Fallback when the transcript yields nothing for a category
_FALLBACK_THEME_TEXT = "Key strategic topics were discussed during the meeting."
_MIN_SENTENCE_WORDS = 4


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract(source_document: SourceDocument) -> list[ExtractedInsight]:
    """Extract structured insights from a meeting transcript.

    Args:
        source_document: A SourceDocument with source_type="zoom_transcript".
                         Must have non-empty content.

    Returns:
        A list of 5–15 ExtractedInsight objects covering themes, decisions,
        actions, risks, and priorities found in the transcript.
    """
    content = source_document.content or ""
    sentences = _split_sentences(content)
    scored = _score_sentences(sentences)

    insights: list[ExtractedInsight] = []

    for category, (_, max_count, base_conf, derivation) in _CATEGORY_CONFIG.items():
        category_sentences = scored.get(category, [])
        selected = category_sentences[:max_count]

        if not selected:
            # Only inject a fallback for "theme" to guarantee non-empty brief
            if category == "theme":
                insights.append(
                    _make_insight(
                        category=category,
                        text=_fallback_theme(source_document.title),
                        confidence=0.60,
                        derivation_type="inferred",
                        source_pointer=None,
                        source_document=source_document,
                        metadata={"fallback": True},
                    )
                )
            continue

        for rank, (sent_idx, sentence, score) in enumerate(selected):
            confidence = _score_to_confidence(base_conf, score, rank)
            insights.append(
                _make_insight(
                    category=category,
                    text=_clean_sentence(sentence),
                    confidence=confidence,
                    derivation_type=derivation,
                    source_pointer=f"sentence:{sent_idx}",
                    source_document=source_document,
                    metadata={"signal_score": score, "rank": rank},
                )
            )

    return insights


# ---------------------------------------------------------------------------
# Sentence splitting
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """Split transcript text into individual sentences.

    Handles common transcript conventions: line breaks, speaker labels,
    full stops, question marks, exclamation marks.
    """
    # Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip speaker labels like "Alice: " or "[00:12:34] Bob:"
    text = re.sub(r"^\s*(\[[^\]]*\]\s*)?[\w\s]+:\s*", "", text, flags=re.MULTILINE)

    # Split on sentence-ending punctuation or newlines
    raw_parts = re.split(r"(?<=[.!?])\s+|\n+", text)

    sentences = []
    for part in raw_parts:
        part = part.strip()
        if part and len(part.split()) >= _MIN_SENTENCE_WORDS:
            sentences.append(part)

    return sentences


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _score_sentences(
    sentences: list[str],
) -> dict[str, list[tuple[int, str, int]]]:
    """Score each sentence against each category's signal bank.

    Returns a dict mapping category → sorted list of (sentence_index, sentence, score)
    tuples, descending by score.  Only sentences with score > 0 are included.
    """
    results: dict[str, list[tuple[int, str, int]]] = {c: [] for c in _CATEGORY_CONFIG}

    for idx, sentence in enumerate(sentences):
        lower = sentence.lower()
        for category, (signals, _, _, _) in _CATEGORY_CONFIG.items():
            score = _count_signals(lower, signals)
            if score > 0:
                results[category].append((idx, sentence, score))

    # Sort each category by score descending
    for category in results:
        results[category].sort(key=lambda x: x[2], reverse=True)

    return results


def _count_signals(text: str, signals: tuple[str, ...]) -> int:
    """Count how many distinct signal phrases appear in the text."""
    return sum(1 for signal in signals if signal in text)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_to_confidence(base: float, score: int, rank: int) -> float:
    """Derive a confidence value from signal score and rank."""
    # More signals → slightly higher confidence; lower rank → slightly lower
    adjusted = base + (score - 1) * 0.03 - rank * 0.04
    return round(max(0.40, min(0.95, adjusted)), 2)


def _clean_sentence(sentence: str) -> str:
    """Ensure sentence ends with a period and is title-appropriate."""
    sentence = sentence.strip()
    if sentence and sentence[-1] not in ".!?":
        sentence += "."
    return sentence


def _fallback_theme(title: str) -> str:
    return f"Key strategic topics were discussed during: {title}."


def _make_insight(
    *,
    category: str,
    text: str,
    confidence: float,
    derivation_type: str,
    source_pointer: str | None,
    source_document: SourceDocument,
    metadata: dict[str, Any],
) -> ExtractedInsight:
    return ExtractedInsight(
        category=category,
        text=text,
        confidence=confidence,
        source_type=source_document.source_type,
        source_id=source_document.source_id,
        source_pointer=source_pointer,
        derivation_type=derivation_type,
        metadata=metadata,
    )
