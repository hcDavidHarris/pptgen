"""Stage 3 extension tests for generate_presentation().

Covers slide_plan, deck_definition, and stage="deck_planned".
Stage 1 and Stage 2 behavioral tests remain in their respective files.
"""

from __future__ import annotations

import pytest

from pptgen.pipeline import PipelineError, PipelineResult, generate_presentation
from pptgen.planner import SlidePlan
from pptgen.spec.presentation_spec import PresentationSpec


# ---------------------------------------------------------------------------
# Stage and new field presence
# ---------------------------------------------------------------------------

class TestStage3PipelineResult:
    def test_stage_is_deck_planned(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert result.stage == "deck_planned"

    def test_slide_plan_is_populated(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert result.slide_plan is not None

    def test_slide_plan_is_correct_type(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert isinstance(result.slide_plan, SlidePlan)

    def test_deck_definition_is_populated(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert result.deck_definition is not None

    def test_deck_definition_is_dict(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert isinstance(result.deck_definition, dict)

    def test_presentation_spec_still_populated(self):
        result = generate_presentation("sprint backlog velocity work items blocked")
        assert isinstance(result.presentation_spec, PresentationSpec)


# ---------------------------------------------------------------------------
# All five playbook routes produce a slide_plan and deck_definition
# ---------------------------------------------------------------------------

class TestAllPlaybooksProducePlan:
    def test_meeting_notes_produces_plan(self):
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Agenda: review action items and decisions."
        )
        assert result.slide_plan is not None
        assert result.deck_definition is not None

    def test_ado_summary_produces_plan(self):
        result = generate_presentation(
            "Sprint 12 complete. Velocity 38 story points. "
            "Backlog groomed. Three work items blocked."
        )
        assert result.slide_plan is not None
        assert result.deck_definition is not None

    def test_architecture_notes_produces_plan(self):
        result = generate_presentation(
            "ADR-007: option A vs option B. Decision record: adopt event-driven. "
            "Tradeoffs documented. System design approved."
        )
        assert result.slide_plan is not None
        assert result.deck_definition is not None

    def test_devops_metrics_produces_plan(self):
        result = generate_presentation(
            "DORA report: deployment frequency 3/day, "
            "change failure rate 1.8%, lead time for changes under 2h, MTTR 12min."
        )
        assert result.slide_plan is not None
        assert result.deck_definition is not None

    def test_unknown_produces_generic_plan(self):
        result = generate_presentation("Random unrelated text about office furniture.")
        assert result.playbook_id == "generic-summary-playbook"
        assert result.slide_plan is not None
        assert result.deck_definition is not None

    def test_empty_produces_generic_plan(self):
        result = generate_presentation("")
        assert result.playbook_id == "generic-summary-playbook"
        assert result.slide_plan is not None
        assert result.deck_definition is not None


# ---------------------------------------------------------------------------
# SlidePlan structural validity
# ---------------------------------------------------------------------------

class TestSlidePlanStructure:
    def test_slide_plan_slide_count_positive(self):
        result = generate_presentation("sprint backlog blocked work items")
        assert result.slide_plan.slide_count >= 2

    def test_slide_plan_first_type_is_title(self):
        result = generate_presentation("sprint backlog blocked work items")
        assert result.slide_plan.planned_slide_types[0] == "title"

    def test_slide_plan_count_equals_deck_slides(self):
        result = generate_presentation("sprint backlog blocked work items")
        assert result.slide_plan.slide_count == len(result.deck_definition["slides"])

    def test_slide_plan_playbook_id_matches_result(self):
        result = generate_presentation("sprint backlog blocked work items")
        assert result.slide_plan.playbook_id == result.playbook_id


# ---------------------------------------------------------------------------
# Deck definition structural validity
# ---------------------------------------------------------------------------

class TestDeckDefinitionStructure:
    def test_deck_definition_has_deck_key(self):
        result = generate_presentation("sprint backlog velocity")
        assert "deck" in result.deck_definition

    def test_deck_definition_has_slides_key(self):
        result = generate_presentation("sprint backlog velocity")
        assert "slides" in result.deck_definition

    def test_deck_slides_is_list(self):
        result = generate_presentation("sprint backlog velocity")
        assert isinstance(result.deck_definition["slides"], list)

    def test_deck_slides_non_empty(self):
        result = generate_presentation("sprint backlog velocity")
        assert len(result.deck_definition["slides"]) >= 1

    def test_first_deck_slide_is_title_type(self):
        result = generate_presentation("meeting notes action items decisions")
        assert result.deck_definition["slides"][0]["type"] == "title"

    def test_deck_metadata_has_title(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.deck_definition["deck"]["title"]

    def test_deck_metadata_has_template(self):
        result = generate_presentation("sprint backlog velocity")
        assert result.deck_definition["deck"]["template"]


# ---------------------------------------------------------------------------
# Slide plan / deck_definition coherence
# ---------------------------------------------------------------------------

class TestPlanDeckCoherence:
    def test_plan_types_match_deck_slide_types(self):
        result = generate_presentation(
            "ADR-007: option A vs option B. Decision record: event-driven."
        )
        deck_types = [s["type"] for s in result.deck_definition["slides"]]
        assert result.slide_plan.planned_slide_types == deck_types


# ---------------------------------------------------------------------------
# Error handling preserved from Stage 1
# ---------------------------------------------------------------------------

class TestErrorHandlingPreserved:
    def test_none_still_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(None)  # type: ignore[arg-type]

    def test_int_still_raises_pipeline_error(self):
        with pytest.raises(PipelineError):
            generate_presentation(42)  # type: ignore[arg-type]
