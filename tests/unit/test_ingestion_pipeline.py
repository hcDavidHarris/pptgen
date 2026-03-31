"""Tests for ingestion_pipeline: run_ingestion end-to-end."""

import pytest

from pptgen.ingestion.ingestion_models import BaseBrief, SourceDocument
from pptgen.ingestion.ingestion_pipeline import run_ingestion
from pptgen.ingestion.source_selector import UnknownSourceTypeError
from pptgen.ingestion.validators.source_payload_validator import SourceValidationError


# ---------------------------------------------------------------------------
# Happy path — each registered source type
# ---------------------------------------------------------------------------


class TestRunIngestionHappyPath:
    @pytest.mark.parametrize("source_type", ["transcript", "ado_board", "ado_repo"])
    def test_returns_base_brief(self, source_type):
        doc = SourceDocument(
            source_type=source_type,
            source_id="id-1",
            title="Test Document",
            content="Some content",
        )
        result = run_ingestion(doc)
        assert isinstance(result, BaseBrief)

    def test_transcript_produces_strategic_brief(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="Q1 Strategy Session",
            content="Discussion content",
        )
        result = run_ingestion(doc)
        assert result.brief_type == "strategic"

    def test_ado_board_produces_delivery_brief(self):
        doc = SourceDocument(
            source_type="ado_board",
            source_id="sprint-10",
            title="Sprint 10 Board",
            content=None,
        )
        result = run_ingestion(doc)
        assert result.brief_type == "delivery"

    def test_ado_repo_produces_architecture_brief(self):
        doc = SourceDocument(
            source_type="ado_repo",
            source_id="repo-main",
            title="Main Repository",
            content=None,
        )
        result = run_ingestion(doc)
        assert result.brief_type == "architecture"

    def test_topic_is_source_title(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="My Meeting Notes",
            content="notes",
        )
        result = run_ingestion(doc)
        assert result.topic == "My Meeting Notes"

    def test_sections_are_non_empty(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="T",
            content="c",
        )
        result = run_ingestion(doc)
        assert len(result.sections) > 0

    def test_provenance_is_non_empty(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="T",
            content="c",
        )
        result = run_ingestion(doc)
        assert len(result.provenance) > 0

    def test_confidence_is_float_or_none(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="T",
            content="c",
        )
        result = run_ingestion(doc)
        assert result.confidence is None or isinstance(result.confidence, float)

    def test_deterministic_output(self):
        doc = SourceDocument(
            source_type="ado_board",
            source_id="s1",
            title="Sprint Board",
            content=None,
        )
        r1 = run_ingestion(doc)
        r2 = run_ingestion(doc)
        assert r1.brief_type == r2.brief_type
        assert r1.topic == r2.topic
        assert r1.sections == r2.sections
        assert r1.confidence == r2.confidence


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------


class TestRunIngestionValidationFailures:
    def test_empty_source_type_raises_source_validation_error(self):
        doc = SourceDocument(
            source_type="",
            source_id=None,
            title="T",
            content="c",
        )
        with pytest.raises(SourceValidationError):
            run_ingestion(doc)

    def test_empty_title_raises_source_validation_error(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="",
            content="c",
        )
        with pytest.raises(SourceValidationError):
            run_ingestion(doc)

    def test_whitespace_title_raises_source_validation_error(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="   ",
            content="c",
        )
        with pytest.raises(SourceValidationError):
            run_ingestion(doc)

    def test_unknown_source_type_raises_error(self):
        doc = SourceDocument(
            source_type="unknown_connector_xyz",
            source_id=None,
            title="Valid Title",
            content="c",
        )
        with pytest.raises(UnknownSourceTypeError):
            run_ingestion(doc)


# ---------------------------------------------------------------------------
# Provenance content
# ---------------------------------------------------------------------------


class TestRunIngestionProvenance:
    def test_provenance_dict_has_required_keys(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id="doc-1",
            title="Meeting",
            content="...",
        )
        result = run_ingestion(doc)
        prov = result.provenance[0]
        assert "source_types" in prov
        assert "extraction_timestamp" in prov
        assert "insight_counts_by_category" in prov
        assert "derivation_summary" in prov
        assert "confidence_summary" in prov

    def test_provenance_source_type_matches_document(self):
        doc = SourceDocument(
            source_type="ado_board",
            source_id="s1",
            title="Board",
            content=None,
        )
        result = run_ingestion(doc)
        prov = result.provenance[0]
        assert "ado_board" in prov["source_types"]
