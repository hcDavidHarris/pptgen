"""Stage 2 extension tests for generate_presentation().

Covers the presentation_spec field added in Stage 2 and the updated stage
value.  The Stage 1 behavioral tests remain in test_generation_pipeline.py.
"""

from __future__ import annotations

import pytest

from pptgen.pipeline import PipelineError, PipelineResult, generate_presentation
from pptgen.spec.presentation_spec import PresentationSpec


# ---------------------------------------------------------------------------
# Stage and spec presence
# ---------------------------------------------------------------------------

class TestStage2PipelineResult:
    def test_stage_is_spec_generated(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert result.stage == "spec_generated"

    def test_presentation_spec_is_populated(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert result.presentation_spec is not None

    def test_presentation_spec_is_correct_type(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert isinstance(result.presentation_spec, PresentationSpec)

    def test_playbook_id_present(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert result.playbook_id == "ado-summary-to-weekly-delivery"


# ---------------------------------------------------------------------------
# All five playbook routes produce specs
# ---------------------------------------------------------------------------

class TestAllPlaybooksProduceSpec:
    def test_meeting_notes_produces_spec(self):
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Agenda: review action items and decisions."
        )
        assert result.playbook_id == "meeting-notes-to-eos-rocks"
        assert result.presentation_spec is not None
        assert result.presentation_spec.title
        assert result.presentation_spec.sections

    def test_ado_summary_produces_spec(self):
        result = generate_presentation(
            "Sprint 12 complete. Velocity 38 story points. "
            "Backlog groomed. Three work items blocked."
        )
        assert result.playbook_id == "ado-summary-to-weekly-delivery"
        assert result.presentation_spec is not None

    def test_architecture_notes_produces_spec(self):
        result = generate_presentation(
            "ADR-007: option A vs option B. Decision record: adopt event-driven. "
            "Tradeoffs documented. System design approved."
        )
        assert result.playbook_id == "architecture-notes-to-adr-deck"
        assert result.presentation_spec is not None

    def test_devops_metrics_produces_spec(self):
        result = generate_presentation(
            "DORA report: deployment frequency 3/day, "
            "change failure rate 1.8%, lead time for changes under 2h, MTTR 12min."
        )
        assert result.playbook_id == "devops-metrics-to-scorecard"
        assert result.presentation_spec is not None

    def test_unknown_produces_generic_spec(self):
        result = generate_presentation("Random unrelated text about office furniture.")
        assert result.playbook_id == "generic-summary-playbook"
        assert result.presentation_spec is not None

    def test_empty_produces_generic_spec(self):
        result = generate_presentation("")
        assert result.playbook_id == "generic-summary-playbook"
        assert result.presentation_spec is not None


# ---------------------------------------------------------------------------
# Spec structural validity
# ---------------------------------------------------------------------------

class TestSpecStructuralValidity:
    def test_spec_title_non_empty(self):
        result = generate_presentation("meeting attendees action items decisions")
        assert result.presentation_spec.title

    def test_spec_subtitle_non_empty(self):
        result = generate_presentation("meeting attendees action items decisions")
        assert result.presentation_spec.subtitle

    def test_spec_has_at_least_one_section(self):
        result = generate_presentation("sprint backlog blocked work items")
        assert len(result.presentation_spec.sections) >= 1

    def test_spec_section_title_non_empty(self):
        result = generate_presentation("adr decision record tradeoff option a option b")
        for section in result.presentation_spec.sections:
            assert section.title


# ---------------------------------------------------------------------------
# Error handling unchanged from Stage 1
# ---------------------------------------------------------------------------

class TestErrorHandlingUnchanged:
    def test_none_still_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(None)  # type: ignore[arg-type]

    def test_int_still_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(42)  # type: ignore[arg-type]
