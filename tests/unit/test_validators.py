"""Tests for ingestion validators: source, insight, and brief."""

import pytest

from pptgen.ingestion.ingestion_models import BaseBrief, ExtractedInsight, SourceDocument
from pptgen.ingestion.validators.brief_validator import BriefValidationError, validate_brief
from pptgen.ingestion.validators.extracted_insight_validator import (
    InsightValidationError,
    validate_insight,
)
from pptgen.ingestion.validators.source_payload_validator import (
    SourceValidationError,
    validate_source,
)


# ---------------------------------------------------------------------------
# validate_source
# ---------------------------------------------------------------------------


class TestValidateSource:
    def test_valid_source_does_not_raise(self):
        doc = SourceDocument(
            source_type="transcript",
            source_id=None,
            title="Valid Title",
            content="content",
        )
        validate_source(doc)  # should not raise

    def test_empty_source_type_raises(self):
        doc = SourceDocument(source_type="", source_id=None, title="T", content=None)
        with pytest.raises(SourceValidationError, match="source_type"):
            validate_source(doc)

    def test_whitespace_source_type_raises(self):
        doc = SourceDocument(source_type="  ", source_id=None, title="T", content=None)
        with pytest.raises(SourceValidationError, match="source_type"):
            validate_source(doc)

    def test_empty_title_raises(self):
        doc = SourceDocument(source_type="transcript", source_id=None, title="", content=None)
        with pytest.raises(SourceValidationError, match="title"):
            validate_source(doc)

    def test_whitespace_title_raises(self):
        doc = SourceDocument(source_type="transcript", source_id=None, title="   ", content=None)
        with pytest.raises(SourceValidationError, match="title"):
            validate_source(doc)

    def test_both_empty_raises_with_combined_message(self):
        doc = SourceDocument(source_type="", source_id=None, title="", content=None)
        with pytest.raises(SourceValidationError):
            validate_source(doc)

    def test_source_id_can_be_none(self):
        doc = SourceDocument(
            source_type="transcript", source_id=None, title="T", content="c"
        )
        validate_source(doc)  # source_id=None is allowed

    def test_content_can_be_none(self):
        doc = SourceDocument(
            source_type="ado_board", source_id="s1", title="T", content=None
        )
        validate_source(doc)  # content=None is allowed


# ---------------------------------------------------------------------------
# validate_insight
# ---------------------------------------------------------------------------


class TestValidateInsight:
    def _make(self, text="Sample text", derivation_type="summarized"):
        return ExtractedInsight(
            category="theme",
            text=text,
            confidence=0.8,
            source_type="transcript",
            source_id=None,
            source_pointer=None,
            derivation_type=derivation_type,
        )

    def test_valid_insight_does_not_raise(self):
        validate_insight(self._make())

    @pytest.mark.parametrize("dtype", ["quoted", "summarized", "inferred", "aggregated"])
    def test_all_valid_derivation_types_pass(self, dtype):
        validate_insight(self._make(derivation_type=dtype))

    def test_empty_text_raises(self):
        with pytest.raises(InsightValidationError, match="text"):
            validate_insight(self._make(text=""))

    def test_whitespace_text_raises(self):
        with pytest.raises(InsightValidationError, match="text"):
            validate_insight(self._make(text="   "))

    def test_invalid_derivation_type_raises(self):
        with pytest.raises(InsightValidationError, match="derivation_type"):
            validate_insight(self._make(derivation_type="guessed"))

    def test_error_message_lists_valid_types(self):
        try:
            validate_insight(self._make(derivation_type="bad_type"))
        except InsightValidationError as e:
            assert "aggregated" in str(e)
            assert "quoted" in str(e)

    def test_both_invalid_raises(self):
        insight = ExtractedInsight(
            category="theme",
            text="",
            confidence=None,
            source_type="x",
            source_id=None,
            source_pointer=None,
            derivation_type="invalid",
        )
        with pytest.raises(InsightValidationError):
            validate_insight(insight)


# ---------------------------------------------------------------------------
# validate_brief
# ---------------------------------------------------------------------------


class TestValidateBrief:
    def _make(
        self,
        topic="My Topic",
        sections=None,
        provenance=None,
    ):
        return BaseBrief(
            brief_type="strategic",
            topic=topic,
            goal="G",
            audience="A",
            sections=sections if sections is not None else [{"title": "S"}],
            provenance=provenance if provenance is not None else [{"source_types": ["t"]}],
        )

    def test_valid_brief_does_not_raise(self):
        validate_brief(self._make())

    def test_empty_topic_raises(self):
        with pytest.raises(BriefValidationError, match="topic"):
            validate_brief(self._make(topic=""))

    def test_whitespace_topic_raises(self):
        with pytest.raises(BriefValidationError, match="topic"):
            validate_brief(self._make(topic="   "))

    def test_empty_sections_raises(self):
        with pytest.raises(BriefValidationError, match="sections"):
            validate_brief(self._make(sections=[]))

    def test_empty_provenance_raises(self):
        with pytest.raises(BriefValidationError, match="provenance"):
            validate_brief(self._make(provenance=[]))

    def test_all_three_invalid_raises(self):
        brief = BaseBrief(
            brief_type="strategic",
            topic="",
            goal="G",
            audience="A",
            sections=[],
            provenance=[],
        )
        with pytest.raises(BriefValidationError):
            validate_brief(brief)

    def test_multiple_sections_valid(self):
        validate_brief(
            self._make(sections=[{"title": "S1"}, {"title": "S2"}, {"title": "S3"}])
        )

    def test_multiple_provenance_entries_valid(self):
        validate_brief(
            self._make(
                provenance=[
                    {"source_types": ["transcript"]},
                    {"source_types": ["ado_board"]},
                ]
            )
        )
