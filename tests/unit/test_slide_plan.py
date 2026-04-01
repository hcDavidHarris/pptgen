"""Unit tests for the SlidePlan and PlannedSlide dataclasses."""

from __future__ import annotations

import pytest

from pptgen.planner.slide_plan import PlannedSlide, SlidePlan


class TestPlannedSlide:
    def test_create_with_required_fields(self):
        slide = PlannedSlide(slide_type="bullets", title="My Section")
        assert slide.slide_type == "bullets"
        assert slide.title == "My Section"

    def test_source_section_title_defaults_to_none(self):
        slide = PlannedSlide(slide_type="title", title="Deck Title")
        assert slide.source_section_title is None

    def test_source_section_title_can_be_set(self):
        slide = PlannedSlide(
            slide_type="section",
            title="Sprint Status",
            source_section_title="Sprint Status",
        )
        assert slide.source_section_title == "Sprint Status"


class TestSlidePlan:
    def _make_plan(self) -> SlidePlan:
        slides = [
            PlannedSlide(slide_type="title", title="T"),
            PlannedSlide(slide_type="bullets", title="S", source_section_title="S"),
        ]
        return SlidePlan(
            playbook_id="test-playbook",
            slide_count=2,
            planned_slide_types=["title", "bullets"],
            section_count=1,
            slides=slides,
        )

    def test_slide_count_matches_slides_list(self):
        plan = self._make_plan()
        assert plan.slide_count == len(plan.slides)

    def test_planned_slide_types_matches_slides(self):
        plan = self._make_plan()
        assert plan.planned_slide_types == [s.slide_type for s in plan.slides]

    def test_section_count_field(self):
        plan = self._make_plan()
        assert plan.section_count == 1

    def test_playbook_id_field(self):
        plan = self._make_plan()
        assert plan.playbook_id == "test-playbook"

    def test_notes_defaults_to_empty_string(self):
        plan = self._make_plan()
        assert plan.notes == ""

    def test_notes_can_be_set(self):
        plan = self._make_plan()
        plan.notes = "fallback used"
        assert plan.notes == "fallback used"

    def test_playbook_id_can_be_none(self):
        plan = SlidePlan(
            playbook_id=None,
            slide_count=1,
            planned_slide_types=["title"],
            section_count=0,
            slides=[PlannedSlide(slide_type="title", title="T")],
        )
        assert plan.playbook_id is None
