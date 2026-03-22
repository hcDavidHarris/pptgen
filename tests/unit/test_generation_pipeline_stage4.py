"""Stage 4 extension tests for generate_presentation().

Covers output_path, stage="rendered", and the rendering step.
Stage 1–3 behavioral tests remain in their respective files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pptgen.pipeline import PipelineError, PipelineResult, generate_presentation
from pptgen.planner import SlidePlan
from pptgen.spec.presentation_spec import PresentationSpec


_FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Stage advancement
# ---------------------------------------------------------------------------

class TestStage4StageField:
    def test_with_output_path_stage_is_rendered(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "Sprint velocity dropped. Backlog has 14 blocked work items.",
            output_path=out,
        )
        assert result.stage == "rendered"

    def test_without_output_path_stage_is_deck_planned(self):
        result = generate_presentation(
            "Sprint velocity dropped. Backlog has 14 blocked work items."
        )
        assert result.stage == "deck_planned"


# ---------------------------------------------------------------------------
# output_path field
# ---------------------------------------------------------------------------

class TestOutputPathField:
    def test_output_path_populated_after_render(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "meeting notes action items decisions", output_path=out
        )
        assert result.output_path is not None

    def test_output_path_matches_requested_path(self, tmp_path):
        out = tmp_path / "deck.pptx"
        result = generate_presentation(
            "meeting notes action items decisions", output_path=out
        )
        assert Path(result.output_path) == out

    def test_output_path_is_none_when_not_requested(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.output_path is None

    def test_output_path_is_string(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity", output_path=out
        )
        assert isinstance(result.output_path, str)


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

class TestRenderedFileOutput:
    def test_output_file_exists(self, tmp_path):
        out = tmp_path / "deck.pptx"
        generate_presentation("sprint backlog velocity", output_path=out)
        assert out.exists()

    def test_output_file_size_is_positive(self, tmp_path):
        out = tmp_path / "deck.pptx"
        generate_presentation("sprint backlog velocity", output_path=out)
        assert out.stat().st_size > 0

    def test_output_dir_created_if_missing(self, tmp_path):
        out = tmp_path / "subdir" / "nested" / "deck.pptx"
        generate_presentation("sprint backlog velocity", output_path=out)
        assert out.exists()


# ---------------------------------------------------------------------------
# All stages still populated after render
# ---------------------------------------------------------------------------

class TestAllFieldsPopulatedAfterRender:
    def test_presentation_spec_still_populated(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity", output_path=out
        )
        assert isinstance(result.presentation_spec, PresentationSpec)

    def test_slide_plan_still_populated(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity", output_path=out
        )
        assert isinstance(result.slide_plan, SlidePlan)

    def test_deck_definition_still_populated(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity", output_path=out
        )
        assert isinstance(result.deck_definition, dict)

    def test_playbook_id_still_correct(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "Sprint 12. Velocity 38 story points. Backlog groomed. Three work items blocked.",
            output_path=out,
        )
        assert result.playbook_id == "ado-summary-to-weekly-delivery"


# ---------------------------------------------------------------------------
# All five playbook routes render successfully
# ---------------------------------------------------------------------------

class TestAllPlaybooksRender:
    def test_meeting_notes_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "meeting_notes.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out)
        assert result.stage == "rendered"
        assert out.exists()

    def test_architecture_notes_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "architecture_notes.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out)
        assert result.stage == "rendered"
        assert out.exists()

    def test_generic_summary_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "generic_summary.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out)
        assert result.playbook_id == "generic-summary-playbook"
        assert result.stage == "rendered"
        assert out.exists()

    def test_empty_input_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation("", output_path=out)
        assert result.playbook_id == "generic-summary-playbook"
        assert result.stage == "rendered"
        assert out.exists()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestStage4Errors:
    def test_none_still_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(None)  # type: ignore[arg-type]

    def test_int_still_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(42)  # type: ignore[arg-type]
