"""Transcript orchestration helpers — Phase 12B.

High-level entry points for the Zoom transcript ingestion vertical slice:

    ingest_transcript_to_brief(payload)
        Runs the full transcript ingestion pipeline and returns a typed
        BaseBrief (StrategicBrief or EOSRocksBrief).

    ingest_transcript_to_content_intent(payload)
        Runs the full ingestion pipeline and translates the resulting brief
        into a ContentIntent ready for the Content Intelligence pipeline.

Usage example
-------------

    from pptgen.ingestion.transcript_orchestrator import (
        ingest_transcript_to_brief,
        ingest_transcript_to_content_intent,
    )

    payload = {
        "title": "Q3 Leadership Meeting",
        "content": "Full transcript text here...",
        "metadata": {
            "meeting_date": "2026-03-31",
            "participants": ["Alice", "Bob", "David"],
        },
    }

    # Option A — get the structured brief
    brief = ingest_transcript_to_brief(payload)

    # Option B — get a ContentIntent for the CI pipeline
    intent = ingest_transcript_to_content_intent(payload)
    # slides = run_content_intelligence(intent)   # CI pipeline call (when available)

Errors
------
    AdapterPayloadError   — payload is missing required fields (title, content)
    SourceValidationError — normalised document failed validation
    BriefValidationError  — produced brief failed validation
"""

from __future__ import annotations

from typing import Any

from .ci_bridge import ContentIntent, brief_to_content_intent
from .ingestion_models import BaseBrief
from .ingestion_pipeline import ingest_from_payload

_ZOOM_SOURCE_TYPE = "zoom_transcript"


def ingest_transcript_to_brief(payload: dict[str, Any]) -> BaseBrief:
    """Run the transcript ingestion pipeline and return a typed BaseBrief.

    Accepts a transcript payload, normalises it via TranscriptAdapter,
    extracts insights using the rule-based TranscriptExtractor, selects
    the appropriate brief type (StrategicBrief or EOSRocksBrief), and
    returns a fully validated brief with provenance.

    Args:
        payload: Transcript payload dict.  Required keys:
                     title   (str) — human-readable meeting label
                     content (str) — raw transcript text
                 Optional keys:
                     source_id    (str)       — meeting or recording identifier
                     metadata     (dict)      — meeting_date, participants,
                                               meeting_type, speaker_map, tags

    Returns:
        A validated BaseBrief of type "strategic" or "eos_rocks".

    Raises:
        AdapterPayloadError:  If title or content is missing or empty.
        SourceValidationError: If the normalised document fails validation.
        BriefValidationError:  If the produced brief fails validation.
    """
    return ingest_from_payload(_ZOOM_SOURCE_TYPE, payload)


def ingest_transcript_to_content_intent(payload: dict[str, Any]) -> ContentIntent:
    """Run the transcript ingestion pipeline and return a ContentIntent.

    Calls ``ingest_transcript_to_brief()`` then translates the brief into a
    ContentIntent via the CI bridge.  The ContentIntent is ready to pass
    directly into ``run_content_intelligence()`` from the CI layer.

    ContentIntent.context carries the full brief sections, confidence,
    brief_type, and provenance so CI stages have access to authoritative
    content seeds from the transcript.

    Args:
        payload: Transcript payload dict (same contract as
                 ``ingest_transcript_to_brief``).

    Returns:
        A ContentIntent populated with topic, goal, audience, and a
        context dict carrying the brief's structured content.

    Raises:
        AdapterPayloadError:  If title or content is missing or empty.
        SourceValidationError: If the normalised document fails validation.
        BriefValidationError:  If the produced brief fails validation.
    """
    brief = ingest_transcript_to_brief(payload)
    return brief_to_content_intent(brief)
