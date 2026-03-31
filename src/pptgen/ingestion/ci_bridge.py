"""CI Bridge — translates a typed BaseBrief into a ContentIntent for the
Content Intelligence pipeline.

Architectural position
----------------------
    BaseBrief          (ingestion layer output)
        ↓
    brief_to_content_intent()
        ↓
    ContentIntent      (CI layer input)
        ↓
    run_content_intelligence()   ← lives in pptgen.content_intelligence

This module preserves the boundary between ingestion and CI.
The ingestion layer produces a brief; the CI layer consumes a ContentIntent.
The bridge is the only place where these two contracts touch.

ContentIntent definition
------------------------
This module defines ``ContentIntent`` locally, mirroring the dataclass in
``pptgen.content_intelligence.content_models``.  The fields and semantics
are identical.  When the CI source module is present the two are
interchangeable; callers that have CI available can pass the result of
``brief_to_content_intent()`` directly into ``run_content_intelligence()``.

ContentIntent fields
--------------------
    topic    (str)             — primary subject for the deck
    goal     (str | None)      — intended outcome or purpose
    audience (str | None)      — target audience description
    context  (dict | None)     — additional structured seed data for the CI
                                 pipeline; carries brief sections, confidence,
                                 brief_type, and source_type so CI stages can
                                 use them as authoritative content seeds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ingestion_models import BaseBrief


# ---------------------------------------------------------------------------
# ContentIntent — mirrors pptgen.content_intelligence.content_models.ContentIntent
# ---------------------------------------------------------------------------


@dataclass
class ContentIntent:
    """Input contract for the Content Intelligence pipeline.

    Mirrors ``pptgen.content_intelligence.content_models.ContentIntent``.
    Defined here so the CI bridge is self-contained and usable even when
    the CI source module has not been restored from its compiled artifact.

    Attributes:
        topic:    Primary subject of the presentation (required).
        goal:     Intended outcome or purpose (optional).
        audience: Target audience description (optional).
        context:  Additional structured seed data.  The bridge populates this
                  with brief sections, confidence, brief_type, and source_type.
    """

    topic: str
    goal: str | None = None
    audience: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Bridge function
# ---------------------------------------------------------------------------


def brief_to_content_intent(brief: BaseBrief) -> ContentIntent:
    """Translate a typed BaseBrief into a ContentIntent for the CI pipeline.

    The brief's topic, goal, and audience map directly to ContentIntent fields.
    Sections, confidence, brief_type, and source_type are packed into the
    ``context`` dict so downstream CI stages can use them as authoritative
    content seeds rather than generating from scratch.

    Context structure:

        {
          "brief_type":   str,                # e.g. "strategic", "eos_rocks"
          "source_type":  str | None,         # e.g. "zoom_transcript"
          "confidence":   float | None,       # aggregate extraction confidence
          "sections": [
            {
              "title":    str,                # e.g. "Theme", "Action"
              "insights": [str, ...]          # ordered insight texts
            },
            ...
          ],
          "provenance":   list[dict],         # provenance records from brief
        }

    Args:
        brief: A populated BaseBrief produced by the ingestion pipeline.

    Returns:
        A ContentIntent ready for ``run_content_intelligence()``.
    """
    context: dict[str, Any] = {
        "brief_type": brief.brief_type,
        "source_type": brief.metadata.get("source_type"),
        "confidence": brief.confidence,
        "sections": brief.sections,
        "provenance": brief.provenance,
    }

    return ContentIntent(
        topic=brief.topic,
        goal=brief.goal if brief.goal else None,
        audience=brief.audience if brief.audience else None,
        context=context,
    )
