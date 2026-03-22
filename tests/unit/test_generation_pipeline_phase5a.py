"""Phase 5A pipeline tests — execution mode and strategy integration."""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.pipeline import PipelineError, generate_presentation
from pptgen.spec.presentation_spec import PresentationSpec


_FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# PipelineResult.mode field
# ---------------------------------------------------------------------------

class TestModeField:
    def test_default_mode_is_deterministic(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.mode == "deterministic"

    def test_explicit_deterministic_mode(self):
        result = generate_presentation("sprint backlog velocity", mode="deterministic")
        assert result.mode == "deterministic"

    def test_ai_mode(self):
        result = generate_presentation("sprint backlog velocity", mode="ai")
        assert result.mode == "ai"

    def test_mode_is_string(self):
        result = generate_presentation("sprint backlog", mode="ai")
        assert isinstance(result.mode, str)


# ---------------------------------------------------------------------------
# Invalid mode
# ---------------------------------------------------------------------------

class TestInvalidMode:
    def test_invalid_mode_raises_pipeline_error(self):
        with pytest.raises(PipelineError, match="Unknown mode"):
            generate_presentation("test", mode="invalid")

    def test_error_message_lists_valid_modes(self):
        with pytest.raises(PipelineError) as exc_info:
            generate_presentation("test", mode="bad-mode")
        assert "deterministic" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Deterministic mode preserves Phase 4 behavior
# ---------------------------------------------------------------------------

class TestDeterministicModePreserved:
    def test_returns_valid_spec(self):
        result = generate_presentation("meeting notes action items decisions")
        assert isinstance(result.presentation_spec, PresentationSpec)

    def test_stage_is_deck_planned(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.stage == "deck_planned"

    def test_stage_rendered_with_output(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation("sprint backlog velocity", output_path=out)
        assert result.stage == "rendered"

    def test_template_id_populated(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.template_id is not None

    def test_correct_playbook_routing(self):
        result = generate_presentation(
            "ADR-007: option A vs B. Decision: event-driven."
        )
        assert result.playbook_id == "architecture-notes-to-adr-deck"


# ---------------------------------------------------------------------------
# AI mode produces valid output
# ---------------------------------------------------------------------------

class TestAIModeOutput:
    def test_returns_valid_spec(self):
        result = generate_presentation("meeting notes action items", mode="ai")
        assert isinstance(result.presentation_spec, PresentationSpec)

    def test_slide_plan_populated(self):
        result = generate_presentation("sprint backlog velocity", mode="ai")
        assert result.slide_plan is not None
        assert result.slide_plan.slide_count >= 2

    def test_deck_definition_populated(self):
        result = generate_presentation("sprint backlog velocity", mode="ai")
        assert isinstance(result.deck_definition, dict)
        assert "slides" in result.deck_definition

    def test_template_id_populated(self):
        result = generate_presentation("sprint backlog velocity", mode="ai")
        assert result.template_id is not None

    def test_ai_renders_successfully(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items: review.",
            output_path=out,
            mode="ai",
        )
        assert result.stage == "rendered"
        assert out.exists()
        assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# AI mode: all five playbook routes render
# ---------------------------------------------------------------------------

class TestAIModeAllRoutes:
    def test_meeting_notes_ai(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "meeting_notes.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out, mode="ai")
        assert result.stage == "rendered"
        assert out.exists()

    def test_architecture_ai(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "architecture_notes.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out, mode="ai")
        assert result.stage == "rendered"
        assert out.exists()

    def test_generic_ai(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "generic_summary.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out, mode="ai")
        assert result.playbook_id == "generic-summary-playbook"
        assert result.stage == "rendered"
        assert out.exists()

    def test_empty_input_ai(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation("", output_path=out, mode="ai")
        assert result.stage == "rendered"


# ---------------------------------------------------------------------------
# Mode + template interaction
# ---------------------------------------------------------------------------

class TestModeWithTemplate:
    def test_ai_mode_with_explicit_template(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity",
            output_path=out,
            mode="ai",
            template_id="executive_brief_v1",
        )
        assert result.template_id == "executive_brief_v1"
        assert result.stage == "rendered"

    def test_deterministic_mode_with_template(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity",
            output_path=out,
            mode="deterministic",
            template_id="architecture_overview_v1",
        )
        assert result.template_id == "architecture_overview_v1"


# ---------------------------------------------------------------------------
# Error handling preserved
# ---------------------------------------------------------------------------

class TestErrorHandlingPreserved:
    def test_none_raises(self):
        with pytest.raises(PipelineError):
            generate_presentation(None)  # type: ignore[arg-type]

    def test_int_raises(self):
        with pytest.raises(PipelineError):
            generate_presentation(42)  # type: ignore[arg-type]

    def test_invalid_template_raises(self):
        with pytest.raises(PipelineError, match="not registered"):
            generate_presentation("test", template_id="nonexistent_v99")
