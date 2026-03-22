"""Unit tests for the generation pipeline (Phase 4 Stage 1 seam)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pptgen.pipeline import PipelineError, PipelineResult, generate_presentation


# ---------------------------------------------------------------------------
# Happy-path routing
# ---------------------------------------------------------------------------

class TestGeneratePresentationRouting:
    def test_meeting_notes_routed(self):
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions."
        )
        assert result.playbook_id == "meeting-notes-to-eos-rocks"

    def test_ado_summary_routed(self):
        result = generate_presentation(
            "Sprint 12 complete. Velocity was 38 story points. "
            "Backlog groomed. Three work items blocked."
        )
        assert result.playbook_id == "ado-summary-to-weekly-delivery"

    def test_architecture_notes_routed(self):
        result = generate_presentation(
            "ADR-007: option A vs option B. Decision record: adopt event-driven architecture. "
            "Tradeoffs documented. System design approved."
        )
        assert result.playbook_id == "architecture-notes-to-adr-deck"

    def test_unknown_text_routes_to_fallback(self):
        result = generate_presentation("Random unrelated text about office furniture.")
        assert result.playbook_id == "generic-summary-playbook"

    def test_empty_string_routes_to_fallback(self):
        result = generate_presentation("")
        assert result.playbook_id == "generic-summary-playbook"


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------

class TestPipelineResultStructure:
    def test_returns_pipeline_result_instance(self):
        result = generate_presentation("sprint backlog velocity")
        assert isinstance(result, PipelineResult)

    def test_stage_is_deck_planned(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.stage == "deck_planned"

    def test_playbook_id_is_string(self):
        result = generate_presentation("sprint backlog velocity")
        assert isinstance(result.playbook_id, str)
        assert len(result.playbook_id) > 0

    def test_input_text_is_normalised(self):
        result = generate_presentation("  sprint backlog  ")
        assert result.input_text == "sprint backlog"

    def test_notes_field_exists(self):
        result = generate_presentation("sprint backlog")
        assert hasattr(result, "notes")
        assert isinstance(result.notes, str)

    def test_empty_input_has_fallback_note(self):
        result = generate_presentation("")
        assert result.notes != "" or result.playbook_id == "generic-summary-playbook"


# ---------------------------------------------------------------------------
# Input normalisation
# ---------------------------------------------------------------------------

class TestInputNormalisation:
    def test_leading_trailing_whitespace_stripped(self):
        result = generate_presentation("   sprint backlog velocity   ")
        assert result.input_text == "sprint backlog velocity"

    def test_uppercase_input_handled(self):
        result = generate_presentation("SPRINT BACKLOG VELOCITY")
        assert result.playbook_id == "ado-summary-to-weekly-delivery"

    def test_multiline_input_handled(self):
        text = "Meeting notes\nAttendees: Alice, Bob\nAction items: review follow-up"
        result = generate_presentation(text)
        assert result.playbook_id == "meeting-notes-to-eos-rocks"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestPipelineErrors:
    def test_none_raises_pipeline_error(self):
        with pytest.raises(PipelineError, match="str"):
            generate_presentation(None)  # type: ignore[arg-type]

    def test_int_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(42)  # type: ignore[arg-type]

    def test_list_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(["sprint"])  # type: ignore[arg-type]

    def test_error_message_includes_type(self):
        with pytest.raises(PipelineError, match="NoneType"):
            generate_presentation(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Delegation — pipeline calls route_input, not reimplemented routing
# ---------------------------------------------------------------------------

class TestDelegation:
    def test_delegates_to_route_input(self):
        """generate_presentation must call route_input rather than
        reimplementing classification logic."""
        with patch(
            "pptgen.pipeline.generation_pipeline.route_input",
            return_value="meeting-notes-to-eos-rocks",
        ) as mock_route:
            result = generate_presentation("some notes text")

        mock_route.assert_called_once_with("some notes text")
        assert result.playbook_id == "meeting-notes-to-eos-rocks"

    def test_returns_route_input_result_unchanged(self):
        """The playbook_id in the result must equal what route_input returned.

        Both route_input and execute_playbook_full are mocked so the sentinel ID
        does not propagate into the real routing table lookup.
        """
        from pptgen.spec.presentation_spec import PresentationSpec, SectionSpec

        sentinel = "custom-playbook-sentinel"
        dummy_spec = PresentationSpec(
            title="T", subtitle="S", sections=[SectionSpec(title="Sec")]
        )
        with (
            patch(
                "pptgen.pipeline.generation_pipeline.route_input",
                return_value=sentinel,
            ),
            patch(
                "pptgen.pipeline.generation_pipeline.execute_playbook_full",
                return_value=(dummy_spec, ""),
            ),
        ):
            result = generate_presentation("any text")

        assert result.playbook_id == sentinel
