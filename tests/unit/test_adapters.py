"""Tests for the Phase 12A.1 adapter layer.

Coverage:
    - Adapter normalization (transcript, ado_board, ado_repo)
    - Adapter selector dispatch
    - Integration: adapter → run_ingestion() end-to-end
    - Protocol conformance
"""

import pytest

from pptgen.ingestion.adapters import (
    AdoBoardAdapter,
    AdoRepoAdapter,
    SourceAdapter,
    TranscriptAdapter,
    UnknownAdapterError,
    select_adapter,
)
from pptgen.ingestion.adapters.base import AdapterPayloadError
from pptgen.ingestion.ingestion_models import BaseBrief, SourceDocument
from pptgen.ingestion.ingestion_pipeline import ingest_from_payload, run_ingestion


# ===========================================================================
# TranscriptAdapter
# ===========================================================================


_TRANSCRIPT_CONTENT = "We discussed Q3 strategy, priorities, and follow-up actions."


class TestTranscriptAdapterNormalization:
    def test_returns_source_document(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "Q1 Strategy", "content": _TRANSCRIPT_CONTENT})
        assert isinstance(result, SourceDocument)

    def test_source_type_is_zoom_transcript(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "Meeting", "content": _TRANSCRIPT_CONTENT})
        assert result.source_type == "zoom_transcript"

    def test_title_is_preserved(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "All Hands April", "content": _TRANSCRIPT_CONTENT})
        assert result.title == "All Hands April"

    def test_title_is_stripped(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "  Leadership Sync  ", "content": _TRANSCRIPT_CONTENT})
        assert result.title == "Leadership Sync"

    def test_source_id_is_passed_through(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "source_id": "zoom-abc-123", "content": _TRANSCRIPT_CONTENT})
        assert result.source_id == "zoom-abc-123"

    def test_source_id_defaults_to_none(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "content": _TRANSCRIPT_CONTENT})
        assert result.source_id is None

    def test_content_is_passed_through(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "content": "Transcript text here."})
        assert result.content == "Transcript text here."

    def test_content_is_stripped(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "content": "  Transcript text.  "})
        assert result.content == "Transcript text."

    def test_missing_content_raises_adapter_payload_error(self):
        adapter = TranscriptAdapter()
        with pytest.raises(AdapterPayloadError, match="content"):
            adapter.load({"title": "T"})

    def test_empty_content_raises_adapter_payload_error(self):
        adapter = TranscriptAdapter()
        with pytest.raises(AdapterPayloadError, match="content"):
            adapter.load({"title": "T", "content": ""})

    def test_whitespace_content_raises_adapter_payload_error(self):
        adapter = TranscriptAdapter()
        with pytest.raises(AdapterPayloadError):
            adapter.load({"title": "T", "content": "   "})

    def test_metadata_is_passed_through(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "content": _TRANSCRIPT_CONTENT,
                               "metadata": {"date": "2026-03-30", "host": "Alice"}})
        assert result.metadata["date"] == "2026-03-30"
        assert result.metadata["host"] == "Alice"

    def test_metadata_defaults_to_empty_dict(self):
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "content": _TRANSCRIPT_CONTENT})
        assert result.metadata == {}

    def test_missing_title_raises_adapter_payload_error(self):
        adapter = TranscriptAdapter()
        with pytest.raises(AdapterPayloadError, match="title"):
            adapter.load({"content": _TRANSCRIPT_CONTENT})

    def test_empty_title_raises_adapter_payload_error(self):
        adapter = TranscriptAdapter()
        with pytest.raises(AdapterPayloadError, match="title"):
            adapter.load({"title": "", "content": _TRANSCRIPT_CONTENT})

    def test_whitespace_title_raises_adapter_payload_error(self):
        adapter = TranscriptAdapter()
        with pytest.raises(AdapterPayloadError):
            adapter.load({"title": "   ", "content": _TRANSCRIPT_CONTENT})


# ===========================================================================
# AdoBoardAdapter
# ===========================================================================


class TestAdoBoardAdapterNormalization:
    def test_returns_source_document(self):
        adapter = AdoBoardAdapter()
        result = adapter.load({"title": "Sprint 42"})
        assert isinstance(result, SourceDocument)

    def test_source_type_is_ado_board(self):
        adapter = AdoBoardAdapter()
        result = adapter.load({"title": "Sprint 42"})
        assert result.source_type == "ado_board"

    def test_title_is_preserved(self):
        adapter = AdoBoardAdapter()
        result = adapter.load({"title": "Sprint 42 — Engineering"})
        assert result.title == "Sprint 42 — Engineering"

    def test_source_id_is_passed_through(self):
        adapter = AdoBoardAdapter()
        result = adapter.load({"title": "T", "source_id": "iteration-42"})
        assert result.source_id == "iteration-42"

    def test_metadata_board_fields_preserved(self):
        adapter = AdoBoardAdapter()
        result = adapter.load({
            "title": "Sprint 42",
            "metadata": {"project": "pptgen", "velocity": 34, "done": 12},
        })
        assert result.metadata["project"] == "pptgen"
        assert result.metadata["velocity"] == 34

    def test_missing_title_raises(self):
        adapter = AdoBoardAdapter()
        with pytest.raises(AdapterPayloadError, match="title"):
            adapter.load({})

    def test_empty_title_raises(self):
        adapter = AdoBoardAdapter()
        with pytest.raises(AdapterPayloadError):
            adapter.load({"title": ""})


# ===========================================================================
# AdoRepoAdapter
# ===========================================================================


class TestAdoRepoAdapterNormalization:
    def test_returns_source_document(self):
        adapter = AdoRepoAdapter()
        result = adapter.load({"title": "pptgen repository"})
        assert isinstance(result, SourceDocument)

    def test_source_type_is_ado_repo(self):
        adapter = AdoRepoAdapter()
        result = adapter.load({"title": "pptgen repository"})
        assert result.source_type == "ado_repo"

    def test_title_is_preserved(self):
        adapter = AdoRepoAdapter()
        result = adapter.load({"title": "platform-core"})
        assert result.title == "platform-core"

    def test_source_id_is_passed_through(self):
        adapter = AdoRepoAdapter()
        result = adapter.load({"title": "T", "source_id": "org/project/pptgen"})
        assert result.source_id == "org/project/pptgen"

    def test_content_readme_passed_through(self):
        adapter = AdoRepoAdapter()
        result = adapter.load({"title": "T", "content": "# README\nA great project."})
        assert "README" in result.content

    def test_metadata_repo_fields_preserved(self):
        adapter = AdoRepoAdapter()
        result = adapter.load({
            "title": "T",
            "metadata": {"language": "Python", "pr_count": 8},
        })
        assert result.metadata["language"] == "Python"

    def test_missing_title_raises(self):
        adapter = AdoRepoAdapter()
        with pytest.raises(AdapterPayloadError, match="title"):
            adapter.load({})


# ===========================================================================
# Adapter metadata isolation
# ===========================================================================


class TestAdapterMetadataIsolation:
    """Verify that adapter does not hold a reference to the original dict."""

    def test_transcript_metadata_is_a_copy(self):
        original_meta = {"key": "value"}
        adapter = TranscriptAdapter()
        result = adapter.load({"title": "T", "content": _TRANSCRIPT_CONTENT,
                               "metadata": original_meta})
        result.metadata["key"] = "mutated"
        assert original_meta["key"] == "value"

    def test_ado_board_metadata_is_a_copy(self):
        original_meta = {"key": "value"}
        adapter = AdoBoardAdapter()
        result = adapter.load({"title": "T", "metadata": original_meta})
        result.metadata["key"] = "mutated"
        assert original_meta["key"] == "value"


# ===========================================================================
# select_adapter
# ===========================================================================


class TestSelectAdapter:
    def test_zoom_transcript_returns_transcript_adapter(self):
        adapter = select_adapter("zoom_transcript")
        assert isinstance(adapter, TranscriptAdapter)

    def test_ado_board_returns_ado_board_adapter(self):
        adapter = select_adapter("ado_board")
        assert isinstance(adapter, AdoBoardAdapter)

    def test_ado_repo_returns_ado_repo_adapter(self):
        adapter = select_adapter("ado_repo")
        assert isinstance(adapter, AdoRepoAdapter)

    def test_each_call_returns_fresh_instance(self):
        a1 = select_adapter("ado_board")
        a2 = select_adapter("ado_board")
        assert a1 is not a2

    def test_unknown_type_raises_unknown_adapter_error(self):
        with pytest.raises(UnknownAdapterError):
            select_adapter("unknown_source_xyz")

    def test_error_message_lists_registered_types(self):
        try:
            select_adapter("bad_type")
        except UnknownAdapterError as e:
            assert "zoom_transcript" in str(e)
            assert "ado_board" in str(e)
            assert "ado_repo" in str(e)


# ===========================================================================
# Protocol conformance
# ===========================================================================


class TestSourceAdapterProtocol:
    def test_transcript_adapter_satisfies_protocol(self):
        assert isinstance(TranscriptAdapter(), SourceAdapter)

    def test_ado_board_adapter_satisfies_protocol(self):
        assert isinstance(AdoBoardAdapter(), SourceAdapter)

    def test_ado_repo_adapter_satisfies_protocol(self):
        assert isinstance(AdoRepoAdapter(), SourceAdapter)


# ===========================================================================
# Integration: adapter → run_ingestion
# ===========================================================================


class TestAdapterIntegrationWithPipeline:
    def test_transcript_adapter_output_flows_through_pipeline(self):
        adapter = TranscriptAdapter()
        doc = adapter.load({"title": "Q1 Strategy Session",
                            "content": "We discussed goals and strategic direction."})
        result = run_ingestion(doc)
        assert isinstance(result, BaseBrief)
        assert result.topic == "Q1 Strategy Session"

    def test_ado_board_adapter_output_flows_through_pipeline(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({"title": "Sprint 42", "source_id": "it-42"})
        result = run_ingestion(doc)
        assert isinstance(result, BaseBrief)
        assert result.brief_type == "delivery"

    def test_ado_repo_adapter_output_flows_through_pipeline(self):
        adapter = AdoRepoAdapter()
        doc = adapter.load({"title": "platform-core", "source_id": "repo/platform"})
        result = run_ingestion(doc)
        assert isinstance(result, BaseBrief)
        assert result.brief_type == "architecture"

    def test_pipeline_result_has_provenance(self):
        adapter = TranscriptAdapter()
        doc = adapter.load({"title": "Meeting", "content": _TRANSCRIPT_CONTENT})
        result = run_ingestion(doc)
        assert len(result.provenance) > 0
        assert result.provenance[0]["source_types"] == ["zoom_transcript"]

    def test_pipeline_result_has_sections(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({"title": "Board"})
        result = run_ingestion(doc)
        assert len(result.sections) > 0


# ===========================================================================
# Integration: ingest_from_payload
# ===========================================================================


class TestIngestFromPayload:
    def test_zoom_transcript_end_to_end(self):
        result = ingest_from_payload(
            "zoom_transcript",
            {"title": "Leadership Sync", "content": "Discussion about priorities."},
        )
        assert isinstance(result, BaseBrief)
        assert result.brief_type == "strategic"
        assert result.topic == "Leadership Sync"

    def test_ado_board_end_to_end(self):
        result = ingest_from_payload(
            "ado_board",
            {"title": "Sprint 10", "source_id": "sprint-10"},
        )
        assert isinstance(result, BaseBrief)
        assert result.brief_type == "delivery"

    def test_ado_repo_end_to_end(self):
        result = ingest_from_payload(
            "ado_repo",
            {"title": "main-repo", "source_id": "org/main-repo"},
        )
        assert isinstance(result, BaseBrief)
        assert result.brief_type == "architecture"

    def test_unknown_source_type_raises_unknown_adapter_error(self):
        with pytest.raises(UnknownAdapterError):
            ingest_from_payload("totally_unknown_type", {"title": "T"})

    def test_missing_title_raises_adapter_payload_error(self):
        with pytest.raises(AdapterPayloadError):
            ingest_from_payload("zoom_transcript", {})

    def test_deterministic_output(self):
        payload = {"title": "Sync", "content": "notes"}
        r1 = ingest_from_payload("zoom_transcript", payload)
        r2 = ingest_from_payload("zoom_transcript", payload)
        assert r1.brief_type == r2.brief_type
        assert r1.topic == r2.topic
        assert r1.sections == r2.sections
