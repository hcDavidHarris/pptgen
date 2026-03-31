"""Tests for provenance: BriefProvenance and build_provenance."""

import pytest

from pptgen.ingestion.ingestion_models import ExtractedInsight
from pptgen.ingestion.provenance import BriefProvenance, build_provenance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_insight(
    category="theme",
    text="Sample text",
    confidence=0.8,
    source_type="transcript",
    source_id="doc-1",
    derivation_type="summarized",
) -> ExtractedInsight:
    return ExtractedInsight(
        category=category,
        text=text,
        confidence=confidence,
        source_type=source_type,
        source_id=source_id,
        source_pointer=None,
        derivation_type=derivation_type,
    )


# ---------------------------------------------------------------------------
# BriefProvenance dataclass
# ---------------------------------------------------------------------------


class TestBriefProvenanceDataclass:
    def test_creation(self):
        prov = BriefProvenance(
            source_types=["transcript"],
            source_ids=["doc-1"],
            extraction_timestamp="2026-01-01T00:00:00+00:00",
            insight_counts_by_category={"theme": 2},
            derivation_summary={"summarized": 2},
            confidence_summary={"min": 0.7, "max": 0.9, "mean": 0.8},
        )
        assert prov.source_types == ["transcript"]
        assert prov.insight_counts_by_category == {"theme": 2}

    def test_to_dict_returns_dict(self):
        prov = BriefProvenance(
            source_types=["transcript"],
            source_ids=[None],
            extraction_timestamp="2026-01-01T00:00:00+00:00",
            insight_counts_by_category={},
            derivation_summary={},
            confidence_summary={"min": None, "max": None, "mean": None},
        )
        d = prov.to_dict()
        assert isinstance(d, dict)
        assert "source_types" in d
        assert "extraction_timestamp" in d
        assert "confidence_summary" in d


# ---------------------------------------------------------------------------
# build_provenance
# ---------------------------------------------------------------------------


class TestBuildProvenance:
    def test_returns_brief_provenance(self):
        insights = [make_insight()]
        prov = build_provenance(insights)
        assert isinstance(prov, BriefProvenance)

    def test_single_insight(self):
        insights = [make_insight(category="theme", confidence=0.8, derivation_type="summarized")]
        prov = build_provenance(insights)
        assert prov.insight_counts_by_category == {"theme": 1}
        assert prov.derivation_summary == {"summarized": 1}
        assert prov.confidence_summary["mean"] == pytest.approx(0.8)
        assert prov.confidence_summary["min"] == pytest.approx(0.8)
        assert prov.confidence_summary["max"] == pytest.approx(0.8)

    def test_multiple_categories(self):
        insights = [
            make_insight(category="theme"),
            make_insight(category="risk"),
            make_insight(category="theme"),
        ]
        prov = build_provenance(insights)
        assert prov.insight_counts_by_category["theme"] == 2
        assert prov.insight_counts_by_category["risk"] == 1

    def test_mixed_derivation_types(self):
        insights = [
            make_insight(derivation_type="summarized"),
            make_insight(derivation_type="inferred"),
            make_insight(derivation_type="summarized"),
        ]
        prov = build_provenance(insights)
        assert prov.derivation_summary["summarized"] == 2
        assert prov.derivation_summary["inferred"] == 1

    def test_source_types_deduplicated(self):
        insights = [
            make_insight(source_type="transcript"),
            make_insight(source_type="transcript"),
            make_insight(source_type="ado_board"),
        ]
        prov = build_provenance(insights)
        assert prov.source_types == ["transcript", "ado_board"]

    def test_source_ids_deduplicated(self):
        insights = [
            make_insight(source_id="a"),
            make_insight(source_id="a"),
            make_insight(source_id="b"),
        ]
        prov = build_provenance(insights)
        assert prov.source_ids == ["a", "b"]

    def test_confidence_none_excluded_from_summary(self):
        insights = [
            make_insight(confidence=None),
            make_insight(confidence=None),
        ]
        prov = build_provenance(insights)
        assert prov.confidence_summary["mean"] is None
        assert prov.confidence_summary["min"] is None
        assert prov.confidence_summary["max"] is None

    def test_confidence_mixed_none_and_values(self):
        insights = [
            make_insight(confidence=0.6),
            make_insight(confidence=None),
            make_insight(confidence=1.0),
        ]
        prov = build_provenance(insights)
        assert prov.confidence_summary["min"] == pytest.approx(0.6)
        assert prov.confidence_summary["max"] == pytest.approx(1.0)
        assert prov.confidence_summary["mean"] == pytest.approx(0.8)

    def test_empty_insights_list(self):
        prov = build_provenance([])
        assert prov.source_types == []
        assert prov.source_ids == []
        assert prov.insight_counts_by_category == {}
        assert prov.derivation_summary == {}
        assert prov.confidence_summary == {"min": None, "max": None, "mean": None}

    def test_extraction_timestamp_is_string(self):
        prov = build_provenance([make_insight()])
        assert isinstance(prov.extraction_timestamp, str)
        assert len(prov.extraction_timestamp) > 0

    def test_deterministic_given_fixed_inputs(self):
        insights = [
            make_insight(category="theme", confidence=0.8),
            make_insight(category="risk", confidence=0.6),
        ]
        p1 = build_provenance(insights)
        p2 = build_provenance(insights)
        assert p1.insight_counts_by_category == p2.insight_counts_by_category
        assert p1.derivation_summary == p2.derivation_summary
        assert p1.confidence_summary == p2.confidence_summary
