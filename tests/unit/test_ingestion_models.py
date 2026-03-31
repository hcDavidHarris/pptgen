"""Tests for ingestion_models: SourceDocument, ExtractedInsight, BaseBrief."""

import pytest

from pptgen.ingestion.ingestion_models import (
    VALID_DERIVATION_TYPES,
    BaseBrief,
    ExtractedInsight,
    SourceDocument,
)


# ---------------------------------------------------------------------------
# SourceDocument
# ---------------------------------------------------------------------------


class TestSourceDocument:
    def test_minimal_creation(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="Q1 Strategy Meeting",
            content="Meeting content here.",
        )
        assert doc.source_type == "transcript"
        assert doc.source_id is None
        assert doc.title == "Q1 Strategy Meeting"
        assert doc.content == "Meeting content here."
        assert doc.metadata == {}

    def test_full_creation(self):
        doc = SourceDocument(
            source_type="ado_board",
            source_id="sprint-42",
            title="Sprint 42 Board",
            content=None,
            metadata={"project": "pptgen", "iteration": 42},
        )
        assert doc.source_id == "sprint-42"
        assert doc.metadata["project"] == "pptgen"
        assert doc.content is None

    def test_metadata_default_is_empty_dict(self):
        doc = SourceDocument(
            source_type="transcript", source_id=None, title="T", content=None
        )
        assert isinstance(doc.metadata, dict)
        assert len(doc.metadata) == 0

    def test_metadata_instances_are_independent(self):
        doc1 = SourceDocument(source_type="a", source_id=None, title="A", content=None)
        doc2 = SourceDocument(source_type="b", source_id=None, title="B", content=None)
        doc1.metadata["key"] = "value"
        assert "key" not in doc2.metadata


# ---------------------------------------------------------------------------
# ExtractedInsight
# ---------------------------------------------------------------------------


class TestExtractedInsight:
    def test_minimal_creation(self):
        insight = ExtractedInsight(
            category="theme",
            text="Example insight",
            confidence=0.8,
            source_type="transcript",
            source_id=None,
            source_pointer=None,
            derivation_type="summarized",
        )
        assert insight.category == "theme"
        assert insight.text == "Example insight"
        assert insight.confidence == 0.8
        assert insight.derivation_type == "summarized"
        assert insight.metadata == {}

    def test_all_valid_derivation_types(self):
        for dtype in ("quoted", "summarized", "inferred", "aggregated"):
            insight = ExtractedInsight(
                category="theme",
                text="text",
                confidence=None,
                source_type="transcript",
                source_id=None,
                source_pointer=None,
                derivation_type=dtype,
            )
            assert insight.derivation_type == dtype

    def test_valid_derivation_types_constant(self):
        assert VALID_DERIVATION_TYPES == frozenset(
            {"quoted", "summarized", "inferred", "aggregated"}
        )

    def test_confidence_can_be_none(self):
        insight = ExtractedInsight(
            category="risk",
            text="Risk text",
            confidence=None,
            source_type="ado_board",
            source_id="s1",
            source_pointer="row:5",
            derivation_type="inferred",
        )
        assert insight.confidence is None

    def test_metadata_default_is_empty_dict(self):
        insight = ExtractedInsight(
            category="c", text="t", confidence=0.5,
            source_type="s", source_id=None, source_pointer=None,
            derivation_type="quoted",
        )
        assert isinstance(insight.metadata, dict)

    def test_metadata_instances_are_independent(self):
        i1 = ExtractedInsight(
            category="a", text="t1", confidence=None,
            source_type="x", source_id=None, source_pointer=None,
            derivation_type="quoted",
        )
        i2 = ExtractedInsight(
            category="b", text="t2", confidence=None,
            source_type="x", source_id=None, source_pointer=None,
            derivation_type="quoted",
        )
        i1.metadata["k"] = "v"
        assert "k" not in i2.metadata


# ---------------------------------------------------------------------------
# BaseBrief
# ---------------------------------------------------------------------------


class TestBaseBrief:
    def test_minimal_creation(self):
        brief = BaseBrief(
            brief_type="strategic",
            topic="Q1 Strategy",
            goal="Align leadership",
            audience="Executive leadership",
        )
        assert brief.brief_type == "strategic"
        assert brief.topic == "Q1 Strategy"
        assert brief.sections == []
        assert brief.metadata == {}
        assert brief.provenance == []
        assert brief.confidence is None

    def test_full_creation(self):
        brief = BaseBrief(
            brief_type="delivery",
            topic="Sprint 42 Summary",
            goal="Communicate delivery status",
            audience="Engineering leadership",
            sections=[{"title": "Delivery", "insights": ["Item A"]}],
            metadata={"source": "ado_board"},
            provenance=[{"source_types": ["ado_board"]}],
            confidence=0.85,
        )
        assert brief.confidence == 0.85
        assert len(brief.sections) == 1
        assert len(brief.provenance) == 1

    def test_mutable_defaults_are_independent(self):
        b1 = BaseBrief(brief_type="strategic", topic="T1", goal="G", audience="A")
        b2 = BaseBrief(brief_type="strategic", topic="T2", goal="G", audience="A")
        b1.sections.append({"title": "X"})
        assert b2.sections == []
