"""Stage 5 extension tests for generate_presentation() — multi-template rendering.

Covers template_id field, template resolution, validation, and override behavior.
Stage 1–4 behavioral tests remain in their respective files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.pipeline import PipelineError, generate_presentation
from pptgen.playbook_engine.template_mapping import (
    _DEFAULT_TEMPLATE_MAP,
    _FALLBACK_TEMPLATE,
    get_default_template,
)


_FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Template mapping module
# ---------------------------------------------------------------------------

class TestTemplateMapping:
    def test_all_five_playbooks_have_defaults(self):
        for pid in [
            "meeting-notes-to-eos-rocks",
            "ado-summary-to-weekly-delivery",
            "architecture-notes-to-adr-deck",
            "devops-metrics-to-scorecard",
            "generic-summary-playbook",
        ]:
            assert get_default_template(pid), f"No default for {pid}"

    def test_architecture_maps_to_architecture_overview(self):
        assert get_default_template("architecture-notes-to-adr-deck") == "architecture_overview_v1"

    def test_ado_maps_to_ops_review(self):
        assert get_default_template("ado-summary-to-weekly-delivery") == "ops_review_v1"

    def test_meeting_notes_maps_to_ops_review(self):
        assert get_default_template("meeting-notes-to-eos-rocks") == "ops_review_v1"

    def test_devops_maps_to_ops_review(self):
        assert get_default_template("devops-metrics-to-scorecard") == "ops_review_v1"

    def test_generic_maps_to_ops_review(self):
        assert get_default_template("generic-summary-playbook") == "ops_review_v1"

    def test_unknown_playbook_returns_fallback(self):
        assert get_default_template("totally-unknown-playbook") == _FALLBACK_TEMPLATE

    def test_all_defaults_are_non_empty_strings(self):
        for pid, tid in _DEFAULT_TEMPLATE_MAP.items():
            assert isinstance(tid, str) and tid, f"Empty template for {pid}"


# ---------------------------------------------------------------------------
# PipelineResult.template_id field
# ---------------------------------------------------------------------------

class TestTemplateIdField:
    def test_template_id_is_populated(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.template_id is not None

    def test_template_id_is_string(self):
        result = generate_presentation("sprint backlog velocity")
        assert isinstance(result.template_id, str)

    def test_template_id_non_empty(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.template_id


# ---------------------------------------------------------------------------
# Default template mapping applied per playbook
# ---------------------------------------------------------------------------

class TestPlaybookDefaultTemplate:
    def test_meeting_notes_uses_ops_review(self):
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and decisions."
        )
        assert result.template_id == "ops_review_v1"

    def test_ado_summary_uses_ops_review(self):
        result = generate_presentation(
            "Sprint 12. Velocity 38 story points. Backlog groomed. Three blocked."
        )
        assert result.template_id == "ops_review_v1"

    def test_architecture_uses_architecture_overview(self):
        result = generate_presentation(
            "ADR-007: option A vs B. Decision record: adopt event-driven."
        )
        assert result.template_id == "architecture_overview_v1"

    def test_devops_uses_ops_review(self):
        result = generate_presentation(
            "DORA: deployment frequency 4/day. Change failure rate 1.8%."
        )
        assert result.template_id == "ops_review_v1"

    def test_generic_uses_ops_review(self):
        result = generate_presentation("Random unrelated text about office furniture.")
        assert result.template_id == "ops_review_v1"


# ---------------------------------------------------------------------------
# Explicit override takes precedence
# ---------------------------------------------------------------------------

class TestTemplateOverride:
    def test_override_wins_over_playbook_default(self):
        result = generate_presentation(
            "ADR: option A vs B. Decision: event-driven.",
            template_id="ops_review_v1",
        )
        # architecture route defaults to architecture_overview_v1; override wins
        assert result.template_id == "ops_review_v1"

    def test_any_valid_template_accepted_for_any_playbook(self):
        result = generate_presentation(
            "Meeting notes action items decisions",
            template_id="executive_brief_v1",
        )
        assert result.template_id == "executive_brief_v1"

    def test_override_to_architecture_template(self):
        result = generate_presentation(
            "Sprint velocity dropped. Backlog has 14 blocked items.",
            template_id="architecture_overview_v1",
        )
        assert result.template_id == "architecture_overview_v1"


# ---------------------------------------------------------------------------
# Registry validation
# ---------------------------------------------------------------------------

class TestTemplateValidation:
    def test_valid_template_id_passes(self):
        # Should not raise
        generate_presentation("test input", template_id="ops_review_v1")

    def test_all_three_registered_templates_pass(self):
        for tid in ["ops_review_v1", "architecture_overview_v1", "executive_brief_v1"]:
            result = generate_presentation("test input", template_id=tid)
            assert result.template_id == tid

    def test_invalid_template_raises_pipeline_error(self):
        with pytest.raises(PipelineError, match="not registered"):
            generate_presentation("test", template_id="nonexistent_v99")

    def test_error_message_lists_registered_templates(self):
        with pytest.raises(PipelineError) as exc_info:
            generate_presentation("test", template_id="bad-template-id")
        msg = str(exc_info.value)
        assert "ops_review_v1" in msg

    def test_invalid_template_fails_before_routing(self):
        """Invalid template should raise before any playbook routing occurs."""
        with pytest.raises(PipelineError):
            generate_presentation("meeting notes action items", template_id="bad-id")

    def test_none_template_does_not_validate(self):
        # None means 'use default' — should not raise
        result = generate_presentation("sprint backlog", template_id=None)
        assert result.template_id is not None


# ---------------------------------------------------------------------------
# Rendering with template override
# ---------------------------------------------------------------------------

class TestRenderWithTemplate:
    def test_ops_review_template_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "Sprint velocity. Backlog 14 blocked.",
            output_path=out,
            template_id="ops_review_v1",
        )
        assert result.stage == "rendered"
        assert out.exists()
        assert out.stat().st_size > 0

    def test_architecture_template_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        text = (_FIXTURES / "architecture_notes.txt").read_text(encoding="utf-8")
        result = generate_presentation(text, output_path=out, template_id="architecture_overview_v1")
        assert result.stage == "rendered"
        assert out.exists()
        assert out.stat().st_size > 0

    def test_executive_brief_template_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and decisions.",
            output_path=out,
            template_id="executive_brief_v1",
        )
        assert result.stage == "rendered"
        assert out.exists()
        assert out.stat().st_size > 0

    def test_template_id_set_in_result_after_render(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity",
            output_path=out,
            template_id="executive_brief_v1",
        )
        assert result.template_id == "executive_brief_v1"

    def test_deck_definition_template_matches_resolved(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(
            "sprint backlog velocity",
            output_path=out,
            template_id="executive_brief_v1",
        )
        assert result.deck_definition["deck"]["template"] == "executive_brief_v1"


# ---------------------------------------------------------------------------
# Stage 4 regression: without template_id still works
# ---------------------------------------------------------------------------

class TestStage4Regression:
    def test_no_template_id_still_renders(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation("sprint backlog velocity", output_path=out)
        assert result.stage == "rendered"
        assert out.exists()

    def test_no_template_id_stage_is_deck_planned(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.stage == "deck_planned"

    def test_non_string_still_raises(self):
        with pytest.raises(PipelineError):
            generate_presentation(None)  # type: ignore[arg-type]
