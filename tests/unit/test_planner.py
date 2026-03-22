"""Unit tests for the slide planning engine (plan_slides)."""

from __future__ import annotations

import pytest

from pptgen.planner import SlidePlan, plan_slides
from pptgen.planner.planning_rules import MAX_BULLETS_PER_SLIDE, MAX_METRICS_PER_SLIDE
from pptgen.spec.presentation_spec import (
    ImageSpec,
    MetricSpec,
    PresentationSpec,
    SectionSpec,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _meeting_spec() -> PresentationSpec:
    return PresentationSpec(
        title="Meeting Notes",
        subtitle="Q3 Planning",
        sections=[
            SectionSpec(
                title="Action Items",
                bullets=["Alice to draft proposal", "Bob to update timeline", "Review Q2 rocks"],
            ),
            SectionSpec(
                title="Decisions",
                bullets=["Adopt new process starting Q3"],
            ),
        ],
    )


def _ado_spec() -> PresentationSpec:
    return PresentationSpec(
        title="Engineering Delivery Summary",
        subtitle="Sprint 12",
        sections=[
            SectionSpec(
                title="Delivery Status",
                bullets=["Velocity: 38 story points", "3 blocked items"],
            ),
            SectionSpec(
                title="Blockers",
                bullets=["Integration pipeline delayed"],
            ),
        ],
    )


def _arch_spec() -> PresentationSpec:
    return PresentationSpec(
        title="Architecture Decision Record",
        subtitle="ADR-007",
        sections=[
            SectionSpec(title="Context", bullets=["Tight coupling via REST"]),
            SectionSpec(title="Options", bullets=["Option A: Azure SB", "Option B: Kafka"]),
            SectionSpec(title="Decision", bullets=["Adopt Azure Service Bus"]),
        ],
    )


def _devops_spec() -> PresentationSpec:
    return PresentationSpec(
        title="DevOps Scorecard",
        subtitle="Q2 DORA",
        sections=[
            SectionSpec(
                title="DORA Metrics",
                metrics=[
                    MetricSpec(label="Deploy Freq", value="3.8/day"),
                    MetricSpec(label="Lead Time", value="1.9h"),
                    MetricSpec(label="MTTR", value="22min"),
                    MetricSpec(label="CFR", value="1.7%"),
                ],
            ),
        ],
    )


def _generic_spec() -> PresentationSpec:
    return PresentationSpec(
        title="Summary",
        subtitle="Overview",
        sections=[
            SectionSpec(title="Overview", bullets=["Budget variance 12%"]),
        ],
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestPlanSlidesReturnType:
    def test_returns_slide_plan_instance(self):
        plan = plan_slides(_meeting_spec())
        assert isinstance(plan, SlidePlan)

    def test_all_playbooks_return_slide_plan(self):
        for spec in [_meeting_spec(), _ado_spec(), _arch_spec(), _devops_spec(), _generic_spec()]:
            assert isinstance(plan_slides(spec), SlidePlan)


# ---------------------------------------------------------------------------
# Title slide invariant
# ---------------------------------------------------------------------------

class TestTitleSlideInvariant:
    def test_first_slide_is_always_title(self):
        for spec in [_meeting_spec(), _ado_spec(), _arch_spec(), _devops_spec(), _generic_spec()]:
            plan = plan_slides(spec)
            assert plan.planned_slide_types[0] == "title"

    def test_title_slide_has_spec_title(self):
        plan = plan_slides(_meeting_spec())
        assert plan.slides[0].title == "Meeting Notes"


# ---------------------------------------------------------------------------
# Slide count coherence
# ---------------------------------------------------------------------------

class TestSlideCountCoherence:
    def test_slide_count_equals_len_slides(self):
        plan = plan_slides(_ado_spec())
        assert plan.slide_count == len(plan.slides)

    def test_planned_slide_types_matches_slides(self):
        plan = plan_slides(_arch_spec())
        assert plan.planned_slide_types == [s.slide_type for s in plan.slides]

    def test_slide_count_at_least_two(self):
        # Title + at least one content slide
        for spec in [_meeting_spec(), _ado_spec(), _arch_spec(), _devops_spec(), _generic_spec()]:
            plan = plan_slides(spec)
            assert plan.slide_count >= 2


# ---------------------------------------------------------------------------
# Section count
# ---------------------------------------------------------------------------

class TestSectionCount:
    def test_section_count_matches_spec(self):
        plan = plan_slides(_arch_spec())
        assert plan.section_count == 3

    def test_section_count_zero_for_empty_spec(self):
        spec = PresentationSpec(title="T", subtitle="S")
        plan = plan_slides(spec)
        assert plan.section_count == 0


# ---------------------------------------------------------------------------
# Empty / minimal spec fallback
# ---------------------------------------------------------------------------

class TestEmptySpecFallback:
    def test_empty_sections_still_produces_plan(self):
        spec = PresentationSpec(title="T", subtitle="S")
        plan = plan_slides(spec)
        assert plan.slide_count >= 2

    def test_empty_sections_includes_overview_slide(self):
        spec = PresentationSpec(title="T", subtitle="S")
        plan = plan_slides(spec)
        assert "bullets" in plan.planned_slide_types

    def test_no_zero_slide_plans(self):
        spec = PresentationSpec(title="T", subtitle="S")
        plan = plan_slides(spec)
        assert plan.slide_count > 0


# ---------------------------------------------------------------------------
# Bullet splitting
# ---------------------------------------------------------------------------

class TestBulletSplitting:
    def test_six_bullets_produce_one_bullets_slide(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", bullets=["b"] * 6)],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("bullets") == 1

    def test_seven_bullets_produce_two_bullets_slides(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", bullets=["b"] * 7)],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("bullets") == 2

    def test_twelve_bullets_produce_two_bullets_slides(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", bullets=["b"] * 12)],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("bullets") == 2

    def test_thirteen_bullets_produce_three_bullets_slides(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", bullets=["b"] * 13)],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("bullets") == 3


# ---------------------------------------------------------------------------
# Metric splitting
# ---------------------------------------------------------------------------

class TestMetricSplitting:
    def _make_metrics(self, n: int) -> list[MetricSpec]:
        return [MetricSpec(label=f"L{i}", value=f"V{i}") for i in range(n)]

    def test_four_metrics_produce_one_metric_slide(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", metrics=self._make_metrics(4))],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("metric_summary") == 1

    def test_five_metrics_produce_two_metric_slides(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", metrics=self._make_metrics(5))],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("metric_summary") == 2


# ---------------------------------------------------------------------------
# Image slides
# ---------------------------------------------------------------------------

class TestImageSlides:
    def test_one_image_produces_one_image_caption_slide(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Arch",
                    images=[ImageSpec(path="diagram.png", caption="System diagram")],
                )
            ],
        )
        plan = plan_slides(spec)
        assert plan.planned_slide_types.count("image_caption") == 1

    def test_image_slide_title_uses_image_title_when_set(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Sec",
                    images=[ImageSpec(path="d.png", caption="C", title="Custom Title")],
                )
            ],
        )
        plan = plan_slides(spec)
        image_slides = [s for s in plan.slides if s.slide_type == "image_caption"]
        assert image_slides[0].title == "Custom Title"

    def test_image_slide_title_falls_back_to_section_title(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(
                    title="Sec",
                    images=[ImageSpec(path="d.png", caption="C")],
                )
            ],
        )
        plan = plan_slides(spec)
        image_slides = [s for s in plan.slides if s.slide_type == "image_caption"]
        assert image_slides[0].title == "Sec"


# ---------------------------------------------------------------------------
# Section divider
# ---------------------------------------------------------------------------

class TestSectionDivider:
    def test_section_divider_included_by_default(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[SectionSpec(title="Sec", bullets=["b"])],
        )
        plan = plan_slides(spec)
        assert "section" in plan.planned_slide_types

    def test_section_divider_excluded_when_disabled(self):
        spec = PresentationSpec(
            title="T", subtitle="S",
            sections=[
                SectionSpec(title="Sec", bullets=["b"], include_section_divider=False)
            ],
        )
        plan = plan_slides(spec)
        assert "section" not in plan.planned_slide_types


# ---------------------------------------------------------------------------
# Playbook ID is recorded
# ---------------------------------------------------------------------------

class TestPlaybookIdRecorded:
    def test_playbook_id_is_set_when_provided(self):
        plan = plan_slides(_meeting_spec(), playbook_id="meeting-notes-to-eos-rocks")
        assert plan.playbook_id == "meeting-notes-to-eos-rocks"

    def test_playbook_id_defaults_to_none(self):
        plan = plan_slides(_meeting_spec())
        assert plan.playbook_id is None


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_spec_same_slide_count(self):
        spec = _devops_spec()
        counts = {plan_slides(spec).slide_count for _ in range(5)}
        assert len(counts) == 1

    def test_same_spec_same_slide_types(self):
        spec = _ado_spec()
        type_lists = {tuple(plan_slides(spec).planned_slide_types) for _ in range(3)}
        assert len(type_lists) == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestPlanSlidesErrors:
    def test_non_spec_raises_type_error(self):
        with pytest.raises(TypeError):
            plan_slides("not a spec")  # type: ignore[arg-type]

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            plan_slides(None)  # type: ignore[arg-type]
