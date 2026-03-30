"""Tests for content intelligence guardrails — Phase 11B."""
from __future__ import annotations

import pytest

from pptgen.content_intelligence.content_models import EnrichedSlideContent, SlideIntent
from pptgen.content_intelligence.guardrails import (
    validate_enriched_content,
    validate_insight_output,
    validate_slide_intent,
)


# ---------------------------------------------------------------------------
# validate_slide_intent
# ---------------------------------------------------------------------------


class TestValidateSlideIntent:
    def test_valid_slide(self):
        si = SlideIntent(title="Cloud Migration: Problem", intent_type="problem", key_points=["pt"])
        assert validate_slide_intent(si) is True

    def test_multiple_key_points_valid(self):
        si = SlideIntent(title="T", intent_type="solution", key_points=["a", "b", "c"])
        assert validate_slide_intent(si) is True

    def test_empty_title_invalid(self):
        si = SlideIntent(title="", intent_type="problem", key_points=["pt"])
        assert validate_slide_intent(si) is False

    def test_whitespace_only_title_invalid(self):
        si = SlideIntent(title="   ", intent_type="problem", key_points=["pt"])
        assert validate_slide_intent(si) is False

    def test_empty_intent_type_invalid(self):
        si = SlideIntent(title="T", intent_type="", key_points=["pt"])
        assert validate_slide_intent(si) is False

    def test_whitespace_intent_type_invalid(self):
        si = SlideIntent(title="T", intent_type="  ", key_points=["pt"])
        assert validate_slide_intent(si) is False

    def test_empty_key_points_invalid(self):
        si = SlideIntent(title="T", intent_type="problem", key_points=[])
        assert validate_slide_intent(si) is False

    def test_non_slide_intent_type_invalid(self):
        assert validate_slide_intent("not a slide") is False  # type: ignore[arg-type]

    def test_none_invalid(self):
        assert validate_slide_intent(None) is False  # type: ignore[arg-type]

    def test_dict_invalid(self):
        assert validate_slide_intent({"title": "T"}) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_enriched_content
# ---------------------------------------------------------------------------


class TestValidateEnrichedContent:
    def _valid(self) -> EnrichedSlideContent:
        return EnrichedSlideContent(
            title="T",
            assertion="Strong, specific claim.",
            supporting_points=["a", "b", "c"],
        )

    def test_valid_content(self):
        assert validate_enriched_content(self._valid()) is True

    def test_four_supporting_points_valid(self):
        c = EnrichedSlideContent(title="T", assertion="A.", supporting_points=["a", "b", "c", "d"])
        assert validate_enriched_content(c) is True

    def test_empty_assertion_invalid(self):
        c = EnrichedSlideContent(title="T", assertion="", supporting_points=["a", "b", "c"])
        assert validate_enriched_content(c) is False

    def test_whitespace_assertion_invalid(self):
        c = EnrichedSlideContent(title="T", assertion="   ", supporting_points=["a", "b", "c"])
        assert validate_enriched_content(c) is False

    def test_none_assertion_invalid(self):
        c = EnrichedSlideContent(title="T", assertion=None, supporting_points=["a", "b", "c"])
        assert validate_enriched_content(c) is False

    def test_two_supporting_points_invalid(self):
        c = EnrichedSlideContent(title="T", assertion="A.", supporting_points=["a", "b"])
        assert validate_enriched_content(c) is False

    def test_zero_supporting_points_invalid(self):
        c = EnrichedSlideContent(title="T", assertion="A.", supporting_points=[])
        assert validate_enriched_content(c) is False

    def test_exactly_three_supporting_points_valid(self):
        c = EnrichedSlideContent(title="T", assertion="A.", supporting_points=["a", "b", "c"])
        assert validate_enriched_content(c) is True

    def test_non_enriched_type_invalid(self):
        assert validate_enriched_content("nope") is False  # type: ignore[arg-type]

    def test_none_invalid(self):
        assert validate_enriched_content(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# validate_insight_output
# ---------------------------------------------------------------------------


class TestValidateInsightOutput:
    def test_one_implication_valid(self):
        c = EnrichedSlideContent(title="T", implications=["This implies action is needed."])
        assert validate_insight_output(c) is True

    def test_multiple_implications_valid(self):
        c = EnrichedSlideContent(title="T", implications=["I1", "I2", "I3"])
        assert validate_insight_output(c) is True

    def test_empty_implications_invalid(self):
        c = EnrichedSlideContent(title="T", implications=[])
        assert validate_insight_output(c) is False

    def test_none_implications_invalid(self):
        c = EnrichedSlideContent(title="T", implications=None)
        assert validate_insight_output(c) is False

    def test_non_enriched_type_invalid(self):
        assert validate_insight_output(42) is False  # type: ignore[arg-type]

    def test_none_invalid(self):
        assert validate_insight_output(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Public re-export from content_intelligence package
# ---------------------------------------------------------------------------


class TestPublicExports:
    def test_validate_slide_intent_exported(self):
        from pptgen.content_intelligence import validate_slide_intent as vi
        assert vi is validate_slide_intent

    def test_validate_enriched_content_exported(self):
        from pptgen.content_intelligence import validate_enriched_content as ve
        assert ve is validate_enriched_content

    def test_validate_insight_output_exported(self):
        from pptgen.content_intelligence import validate_insight_output as vo
        assert vo is validate_insight_output
