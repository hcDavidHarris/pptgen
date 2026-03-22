"""Unit tests for planning_rules constants."""

from __future__ import annotations

from pptgen.planner.planning_rules import MAX_BULLETS_PER_SLIDE, MAX_METRICS_PER_SLIDE


class TestPlanningRulesExist:
    def test_max_bullets_per_slide_exists(self):
        assert MAX_BULLETS_PER_SLIDE is not None

    def test_max_metrics_per_slide_exists(self):
        assert MAX_METRICS_PER_SLIDE is not None


class TestPlanningRulesValues:
    def test_max_bullets_per_slide_is_six(self):
        assert MAX_BULLETS_PER_SLIDE == 6

    def test_max_metrics_per_slide_is_four(self):
        assert MAX_METRICS_PER_SLIDE == 4

    def test_max_bullets_per_slide_is_int(self):
        assert isinstance(MAX_BULLETS_PER_SLIDE, int)

    def test_max_metrics_per_slide_is_int(self):
        assert isinstance(MAX_METRICS_PER_SLIDE, int)

    def test_max_bullets_per_slide_is_positive(self):
        assert MAX_BULLETS_PER_SLIDE > 0

    def test_max_metrics_per_slide_is_positive(self):
        assert MAX_METRICS_PER_SLIDE > 0
