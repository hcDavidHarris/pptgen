"""Content Intelligence data models — Phase 11A / 11C.

Core serializable models for the content intelligence layer.
All models use dataclasses and provide to_dict() for serialization.

Phase 11C additions:
    SlideIntent.primitive       — semantic primitive name assigned by the selector
    EnrichedSlideContent.primitive — propagated from SlideIntent through the pipeline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentIntent:
    """Represents initial authoring input for the content intelligence layer."""

    topic: str
    goal: Optional[str] = None
    audience: Optional[str] = None
    context: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "goal": self.goal,
            "audience": self.audience,
            "context": self.context,
        }


@dataclass
class SlideIntent:
    """Represents a single slide's purpose within a narrative.

    Phase 11C: ``primitive`` is the semantic primitive name assigned by
    the primitive selector.  None before the selector runs.
    """

    title: str
    intent_type: str  # e.g. "problem", "solution", "impact", "metrics"
    key_points: list[str] = field(default_factory=list)
    primitive: Optional[str] = None  # Phase 11C — set by primitive_selector

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "intent_type": self.intent_type,
            "key_points": self.key_points,
            "primitive": self.primitive,
        }


@dataclass
class EnrichedSlideContent:
    """Represents expanded, high-density content for a single slide.

    Phase 11C: ``primitive`` is propagated from the SlideIntent through the
    content expansion stage and exposed via the normalizer's _ci_metadata.
    """

    title: str
    assertion: Optional[str] = None
    supporting_points: list[str] = field(default_factory=list)
    implications: Optional[list[str]] = None
    metadata: dict = field(default_factory=dict)
    primitive: Optional[str] = None  # Phase 11C — propagated from SlideIntent

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "assertion": self.assertion,
            "supporting_points": self.supporting_points,
            "implications": self.implications,
            "metadata": self.metadata,
            "primitive": self.primitive,
        }
