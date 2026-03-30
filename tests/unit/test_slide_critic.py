"""Tests for the slide critic — Phase 11A."""

from __future__ import annotations

from pptgen.content_intelligence import EnrichedSlideContent, critique_slide


class TestCritiqueSlide:
    def test_returns_enriched_slide_content(self):
        esc = EnrichedSlideContent(
            title="T",
            assertion="A",
            supporting_points=["P1", "P2", "P3"],
        )
        result = critique_slide(esc)
        assert isinstance(result, EnrichedSlideContent)

    def test_title_preserved(self):
        esc = EnrichedSlideContent(title="My Title", supporting_points=["a", "b", "c"])
        result = critique_slide(esc)
        assert result.title == "My Title"

    def test_empty_assertion_is_filled(self):
        esc = EnrichedSlideContent(
            title="Some Slide",
            assertion=None,
            supporting_points=["a", "b", "c"],
        )
        result = critique_slide(esc)
        assert result.assertion is not None
        assert len(result.assertion) > 0

    def test_assertion_derived_from_title_when_missing(self):
        esc = EnrichedSlideContent(
            title="Deployment Strategy",
            assertion=None,
            supporting_points=["a", "b", "c"],
        )
        result = critique_slide(esc)
        assert "Deployment Strategy" in result.assertion

    def test_existing_assertion_preserved(self):
        esc = EnrichedSlideContent(
            title="T",
            assertion="Custom assertion.",
            supporting_points=["a", "b", "c"],
        )
        result = critique_slide(esc)
        assert result.assertion == "Custom assertion."

    def test_auto_expands_to_minimum_three_supporting_points(self):
        esc = EnrichedSlideContent(
            title="T",
            assertion="A",
            supporting_points=["Only one."],
        )
        result = critique_slide(esc)
        assert len(result.supporting_points) >= 3

    def test_exactly_zero_supporting_points_expands_to_three(self):
        esc = EnrichedSlideContent(title="T", assertion="A", supporting_points=[])
        result = critique_slide(esc)
        assert len(result.supporting_points) == 3

    def test_three_or_more_supporting_points_unchanged(self):
        pts = ["P1", "P2", "P3", "P4"]
        esc = EnrichedSlideContent(title="T", assertion="A", supporting_points=pts)
        result = critique_slide(esc)
        assert result.supporting_points[:4] == pts

    def test_critic_applied_in_metadata(self):
        esc = EnrichedSlideContent(title="T", assertion="A", supporting_points=["a", "b", "c"])
        result = critique_slide(esc)
        assert result.metadata.get("critic_applied") is True

    def test_implications_passed_through(self):
        esc = EnrichedSlideContent(
            title="T",
            assertion="A",
            supporting_points=["a", "b", "c"],
            implications=["Implication X"],
        )
        result = critique_slide(esc)
        assert result.implications == ["Implication X"]

    def test_is_deterministic(self):
        esc = EnrichedSlideContent(title="T", supporting_points=[])
        r1 = critique_slide(esc)
        r2 = critique_slide(esc)
        assert r1.to_dict() == r2.to_dict()
