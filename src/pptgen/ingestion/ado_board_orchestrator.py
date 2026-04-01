"""ADO Board orchestration helpers — Phase 12C.

High-level entry points for the ADO Board ingestion vertical slice:

    ingest_ado_board_to_brief(payload)
        Runs the full ADO board ingestion pipeline and returns a typed
        DeliveryBrief.

    ingest_ado_board_to_content_intent(payload)
        Runs the full ingestion pipeline and translates the resulting brief
        into a ContentIntent ready for the Content Intelligence pipeline.

Usage example
-------------

    from pptgen.ingestion.ado_board_orchestrator import (
        ingest_ado_board_to_brief,
        ingest_ado_board_to_content_intent,
    )

    payload = {
        "title": "Q3 Delivery Status",
        "metadata": {
            "work_items": [
                {
                    "id": 101,
                    "title": "Build ingestion routing",
                    "state": "In Progress",
                    "type": "Feature",
                    "owner": "Alice",
                    "priority": 1,
                    "tags": ["platform", "phase12c"],
                    "created_date": "2026-03-20",
                    "updated_date": "2026-03-29",
                }
            ],
            "iteration": "Sprint 42",
            "team": "Interchange",
            "date": "2026-04-01",
        },
    }

    # Option A — get the structured brief
    brief = ingest_ado_board_to_brief(payload)

    # Option B — get a ContentIntent for the CI pipeline
    intent = ingest_ado_board_to_content_intent(payload)
    # slides = run_content_intelligence(intent)   # CI pipeline call (when available)

Errors
------
    AdapterPayloadError   — payload is missing required fields (title)
    SourceValidationError — normalised document failed validation
    BriefValidationError  — produced brief failed validation
"""

from __future__ import annotations

from typing import Any

from .ci_bridge import ContentIntent, brief_to_content_intent
from .ingestion_models import BaseBrief
from .ingestion_pipeline import ingest_from_payload

_ADO_BOARD_SOURCE_TYPE = "ado_board"


def ingest_ado_board_to_brief(payload: dict[str, Any]) -> BaseBrief:
    """Run the ADO board ingestion pipeline and return a typed DeliveryBrief.

    Accepts an ADO board payload, normalises it via AdoBoardAdapter,
    extracts insights using the rule-based AdoBoardExtractor, and returns
    a fully validated DeliveryBrief with provenance.

    Args:
        payload: ADO board payload dict.  Required keys:
                     title   (str) — human-readable board / sprint label
                 Optional keys:
                     source_id    (str)       — board or iteration identifier
                     content      (str)       — pre-serialised summary text
                     metadata     (dict)      — work_items, iteration,
                                               team, date

    Returns:
        A validated BaseBrief of type "delivery".

    Raises:
        AdapterPayloadError:  If title is missing or empty.
        SourceValidationError: If the normalised document fails validation.
        BriefValidationError:  If the produced brief fails validation.
    """
    return ingest_from_payload(_ADO_BOARD_SOURCE_TYPE, payload)


def ingest_ado_board_to_content_intent(payload: dict[str, Any]) -> ContentIntent:
    """Run the ADO board ingestion pipeline and return a ContentIntent.

    Calls ``ingest_ado_board_to_brief()`` then translates the brief into a
    ContentIntent via the CI bridge.  The ContentIntent is ready to pass
    directly into ``run_content_intelligence()`` from the CI layer.

    ContentIntent.context carries the full brief sections, confidence,
    brief_type ("delivery"), and provenance so CI stages have access to
    authoritative content seeds from the board.

    Args:
        payload: ADO board payload dict (same contract as
                 ``ingest_ado_board_to_brief``).

    Returns:
        A ContentIntent populated with topic, goal, audience, and a
        context dict carrying the brief's structured content.

    Raises:
        AdapterPayloadError:  If title is missing or empty.
        SourceValidationError: If the normalised document fails validation.
        BriefValidationError:  If the produced brief fails validation.
    """
    brief = ingest_ado_board_to_brief(payload)
    return brief_to_content_intent(brief)
