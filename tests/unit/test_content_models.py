"""Tests for content intelligence data models — Phase 11A."""

from __future__ import annotations

import pytest

from pptgen.content_intelligence import ContentIntent, EnrichedSlideContent, SlideIntent


# ---------------------------------------------------------------------------
# ContentIntent
# ---------------------------------------------------------------------------


class TestContentIntent:
    def test_minimal(self):
        ci = ContentIntent(topic="Cloud Migration")
        assert ci.topic == "Cloud Migration"
        assert ci.goal is None
        assert ci.audience is None
        assert ci.context is None

    def test_full(self):
        ci = ContentIntent(
            topic="Cloud Migration",
            goal="Reduce costs",
            audience="Engineering leadership",
            context={"quarter": "Q2"},
        )
        assert ci.goal == "Reduce costs"
        assert ci.context == {"quarter": "Q2"}

    def test_to_dict_minimal(self):
        ci = ContentIntent(topic="AI Strategy")
        d = ci.to_dict()
        assert d["topic"] == "AI Strategy"
        assert d["goal"] is None
        assert d["audience"] is None
        assert d["context"] is None

    def test_to_dict_full(self):
        ci = ContentIntent(topic="T", goal="G", audience="A", context={"k": "v"})
        d = ci.to_dict()
        assert d == {"topic": "T", "goal": "G", "audience": "A", "context": {"k": "v"}}

    def test_to_dict_is_serializable(self):
        import json
        ci = ContentIntent(topic="Ops Review", goal="align teams")
        json.dumps(ci.to_dict())  # must not raise


# ---------------------------------------------------------------------------
# SlideIntent
# ---------------------------------------------------------------------------


class TestSlideIntent:
    def test_defaults(self):
        si = SlideIntent(title="The Problem", intent_type="problem")
        assert si.key_points == []

    def test_with_key_points(self):
        si = SlideIntent(
            title="Our Solution",
            intent_type="solution",
            key_points=["Point A", "Point B"],
        )
        assert len(si.key_points) == 2

    def test_to_dict(self):
        si = SlideIntent(title="T", intent_type="impact", key_points=["x"])
        d = si.to_dict()
        # Phase 11C: primitive field included in to_dict(); None when unset.
        assert d == {"title": "T", "intent_type": "impact", "key_points": ["x"], "primitive": None}

    def test_to_dict_with_primitive(self):
        si = SlideIntent(title="T", intent_type="problem", key_points=["x"], primitive="problem_statement")
        d = si.to_dict()
        assert d["primitive"] == "problem_statement"


# ---------------------------------------------------------------------------
# EnrichedSlideContent
# ---------------------------------------------------------------------------


class TestEnrichedSlideContent:
    def test_defaults(self):
        esc = EnrichedSlideContent(title="Slide Title")
        assert esc.assertion is None
        assert esc.supporting_points == []
        assert esc.implications is None
        assert esc.metadata == {}

    def test_to_dict(self):
        esc = EnrichedSlideContent(
            title="T",
            assertion="A",
            supporting_points=["P1", "P2", "P3"],
            implications=["I1"],
            metadata={"source": "test"},
        )
        d = esc.to_dict()
        assert d["title"] == "T"
        assert d["assertion"] == "A"
        assert d["supporting_points"] == ["P1", "P2", "P3"]
        assert d["implications"] == ["I1"]
        assert d["metadata"] == {"source": "test"}

    def test_to_dict_is_serializable(self):
        import json
        esc = EnrichedSlideContent(
            title="T",
            supporting_points=["a", "b", "c"],
            metadata={"x": 1},
        )
        json.dumps(esc.to_dict())  # must not raise
