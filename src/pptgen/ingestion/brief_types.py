"""Typed Brief taxonomy for Phase 12A.

Each brief type is a factory function that returns a pre-configured BaseBrief.
This keeps the taxonomy explicit without inheritance complexity.

Supported types:
    strategic      -> StrategicBrief
    delivery       -> DeliveryBrief
    architecture   -> ArchitectureBrief
    eos_rocks      -> EOSRocksBrief
"""

from __future__ import annotations

from typing import Any

from .ingestion_models import BaseBrief

# ---------------------------------------------------------------------------
# Type constants
# ---------------------------------------------------------------------------

BRIEF_TYPE_STRATEGIC = "strategic"
BRIEF_TYPE_DELIVERY = "delivery"
BRIEF_TYPE_ARCHITECTURE = "architecture"
BRIEF_TYPE_EOS_ROCKS = "eos_rocks"

VALID_BRIEF_TYPES: frozenset[str] = frozenset(
    {BRIEF_TYPE_STRATEGIC, BRIEF_TYPE_DELIVERY, BRIEF_TYPE_ARCHITECTURE, BRIEF_TYPE_EOS_ROCKS}
)

# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def StrategicBrief(
    topic: str,
    goal: str = "Align leadership on strategic direction and priorities",
    audience: str = "Executive leadership",
    sections: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    provenance: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
) -> BaseBrief:
    """Factory for a strategic-type brief.

    Suitable for: board updates, strategy reviews, vision alignment.
    """
    return BaseBrief(
        brief_type=BRIEF_TYPE_STRATEGIC,
        topic=topic,
        goal=goal,
        audience=audience,
        sections=sections or [],
        metadata=metadata or {},
        provenance=provenance or [],
        confidence=confidence,
    )


def DeliveryBrief(
    topic: str,
    goal: str = "Communicate delivery status, blockers, and outcomes",
    audience: str = "Engineering and product leadership",
    sections: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    provenance: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
) -> BaseBrief:
    """Factory for a delivery-type brief.

    Suitable for: sprint reviews, release summaries, ADO board exports.
    """
    return BaseBrief(
        brief_type=BRIEF_TYPE_DELIVERY,
        topic=topic,
        goal=goal,
        audience=audience,
        sections=sections or [],
        metadata=metadata or {},
        provenance=provenance or [],
        confidence=confidence,
    )


def ArchitectureBrief(
    topic: str,
    goal: str = "Communicate architectural decisions, trade-offs, and direction",
    audience: str = "Engineering leadership and principal engineers",
    sections: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    provenance: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
) -> BaseBrief:
    """Factory for an architecture-type brief.

    Suitable for: ADR reviews, system design presentations, tech radar updates.
    """
    return BaseBrief(
        brief_type=BRIEF_TYPE_ARCHITECTURE,
        topic=topic,
        goal=goal,
        audience=audience,
        sections=sections or [],
        metadata=metadata or {},
        provenance=provenance or [],
        confidence=confidence,
    )


def EOSRocksBrief(
    topic: str,
    goal: str = "Review quarterly Rocks status and accountability",
    audience: str = "Leadership team",
    sections: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    provenance: list[dict[str, Any]] | None = None,
    confidence: float | None = None,
) -> BaseBrief:
    """Factory for an EOS Rocks-type brief.

    Suitable for: quarterly L10 reviews, EOS Rocks accountability meetings.
    """
    return BaseBrief(
        brief_type=BRIEF_TYPE_EOS_ROCKS,
        topic=topic,
        goal=goal,
        audience=audience,
        sections=sections or [],
        metadata=metadata or {},
        provenance=provenance or [],
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Dispatch map: source_type -> brief factory
# ---------------------------------------------------------------------------

_SOURCE_TYPE_TO_BRIEF_FACTORY = {
    # Legacy direct-path entry (Phase 12A) — kept for backwards compat
    "transcript": StrategicBrief,
    # Adapter-normalised path (Phase 12B+) — resolved dynamically; see below
    "zoom_transcript": StrategicBrief,
    "ado_board": DeliveryBrief,
    "ado_repo": ArchitectureBrief,
    "eos": EOSRocksBrief,
}

_DEFAULT_BRIEF_FACTORY = StrategicBrief

# Meeting types that explicitly request EOS Rocks framing
_EOS_MEETING_TYPES: frozenset[str] = frozenset({"eos", "l10", "rocks", "quarterly"})

# Thresholds for signal-based EOS detection
_EOS_MIN_PRIORITY_INSIGHTS = 3
_EOS_MIN_ACTION_INSIGHTS = 2


def get_brief_factory(source_type: str):
    """Return the brief factory function for the given source type.

    For zoom_transcript, prefer ``select_zoom_transcript_brief_factory()``
    which inspects metadata and insights for a more accurate selection.

    Falls back to StrategicBrief for unknown source types.
    """
    return _SOURCE_TYPE_TO_BRIEF_FACTORY.get(source_type, _DEFAULT_BRIEF_FACTORY)


def select_zoom_transcript_brief_factory(
    metadata: dict[str, Any],
    insights: list[Any],
) -> Any:
    """Choose StrategicBrief or EOSRocksBrief for a zoom_transcript source.

    Selection rule (explicit and deterministic):

    1. If ``metadata["meeting_type"]`` is one of "eos", "l10", "rocks",
       or "quarterly" → EOSRocksBrief.
    2. If the extracted insights contain ≥3 priority insights AND
       ≥2 action insights → EOSRocksBrief.
    3. Otherwise → StrategicBrief.

    Args:
        metadata: The source document's metadata dict.
        insights: The list of ExtractedInsight objects from the extractor.

    Returns:
        EOSRocksBrief factory or StrategicBrief factory.
    """
    # Rule 1 — explicit metadata flag takes precedence
    meeting_type = str(metadata.get("meeting_type", "")).lower().strip()
    if meeting_type in _EOS_MEETING_TYPES:
        return EOSRocksBrief

    # Rule 2 — signal-based detection from extracted insights
    priority_count = sum(1 for i in insights if getattr(i, "category", "") == "priority")
    action_count = sum(1 for i in insights if getattr(i, "category", "") == "action")
    if priority_count >= _EOS_MIN_PRIORITY_INSIGHTS and action_count >= _EOS_MIN_ACTION_INSIGHTS:
        return EOSRocksBrief

    # Rule 3 — default
    return StrategicBrief
