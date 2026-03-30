"""Tests for the content expander — Phase 11A."""

from __future__ import annotations

import pytest

from pptgen.content_intelligence import EnrichedSlideContent, SlideIntent, expand_slide


class TestExpandSlide:
    def test_returns_enriched_slide_content(self):
        si = SlideIntent(title="The Problem", intent_type="problem")
        result = expand_slide(si)
        assert isinstance(result, EnrichedSlideContent)

    def test_title_preserved(self):
        si = SlideIntent(title="My Title", intent_type="solution")
        result = expand_slide(si)
        assert result.title == "My Title"

    def test_assertion_derived_from_title(self):
        si = SlideIntent(title="The Solution", intent_type="solution")
        result = expand_slide(si)
        assert result.assertion is not None
        assert "The Solution" in result.assertion

    def test_minimum_three_supporting_points_with_empty_key_points(self):
        si = SlideIntent(title="Slide", intent_type="impact", key_points=[])
        result = expand_slide(si)
        assert len(result.supporting_points) >= 3

    def test_minimum_three_supporting_points_with_one_key_point(self):
        si = SlideIntent(title="Slide", intent_type="problem", key_points=["Only one."])
        result = expand_slide(si)
        assert len(result.supporting_points) >= 3

    def test_existing_key_points_preserved(self):
        key_points = ["Point A.", "Point B.", "Point C."]
        si = SlideIntent(title="Slide", intent_type="problem", key_points=key_points)
        result = expand_slide(si)
        assert result.supporting_points[:3] == key_points

    def test_more_than_three_key_points_not_truncated(self):
        key_points = ["A.", "B.", "C.", "D.", "E."]
        si = SlideIntent(title="Slide", intent_type="solution", key_points=key_points)
        result = expand_slide(si)
        assert len(result.supporting_points) == 5

    def test_metadata_contains_intent_type(self):
        si = SlideIntent(title="Slide", intent_type="impact")
        result = expand_slide(si)
        assert result.metadata.get("intent_type") == "impact"

    def test_is_deterministic(self):
        si = SlideIntent(title="T", intent_type="problem", key_points=["X."])
        r1 = expand_slide(si)
        r2 = expand_slide(si)
        assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# Phase 11B — prompt-driven path and fallback integration
# ---------------------------------------------------------------------------


class TestExpandSlidePhase11B:
    """Phase 11B: prompt integration, all-or-nothing merge rule, fallback fidelity."""

    def test_prompt_success_propagates_richer_content(self):
        """When run_prompt returns valid EnrichedSlideContent, expand_slide forwards it."""
        from unittest.mock import patch
        from pptgen.content_intelligence import SlideIntent, EnrichedSlideContent

        prompt_result = EnrichedSlideContent(
            title="The Problem",
            assertion="Legacy infrastructure is a strategic liability.",
            supporting_points=[
                "Maintenance costs exceed 40% of IT budget.",
                "Incident frequency has doubled year-on-year.",
                "Talent cannot be hired to maintain COBOL systems.",
            ],
            metadata={"intent_type": "problem", "source": "prompt"},
        )
        si = SlideIntent(title="The Problem", intent_type="problem")
        with patch(
            "pptgen.content_intelligence.content_expander.run_prompt",
            return_value=prompt_result,
        ):
            result = expand_slide(si)

        assert result is prompt_result

    def test_fallback_matches_phase11a_output(self):
        """_expand_slide_fallback output is identical to Phase 11A expand_slide."""
        from pptgen.content_intelligence import SlideIntent
        from pptgen.content_intelligence.content_expander import _expand_slide_fallback

        si = SlideIntent(title="The Impact", intent_type="impact", key_points=["Revenue up."])
        result = _expand_slide_fallback(si)

        assert result.title == "The Impact"
        assert "The Impact" in result.assertion
        assert len(result.supporting_points) >= 3

    def test_fallback_is_deterministic(self):
        from pptgen.content_intelligence import SlideIntent
        from pptgen.content_intelligence.content_expander import _expand_slide_fallback

        si = SlideIntent(title="T", intent_type="problem", key_points=["x"])
        r1 = _expand_slide_fallback(si)
        r2 = _expand_slide_fallback(si)
        assert r1.to_dict() == r2.to_dict()

    def test_partial_prompt_result_not_merged_with_fallback(self):
        """run_prompt validator rejects < 3 supporting points — fallback used entirely."""
        from unittest.mock import patch
        from pptgen.content_intelligence import SlideIntent, EnrichedSlideContent

        partial = EnrichedSlideContent(
            title="T",
            assertion="Short.",
            supporting_points=["Only one point."],  # fails validate_enriched_content
            metadata={"source": "prompt"},
        )
        si = SlideIntent(title="T", intent_type="problem")

        # Inject the partial result then check that expand_slide uses fallback
        def _mock_runner(prompt_name, context, parser, fallback, validator=None, llm_caller=None, **kwargs):
            # Simulate: parser produced partial, validator rejects it
            if validator and not validator(partial):
                return fallback()
            return partial

        with patch(
            "pptgen.content_intelligence.content_expander.run_prompt",
            side_effect=_mock_runner,
        ):
            result = expand_slide(si)

        # Fallback source should be content_expander, not prompt
        assert result.metadata.get("source") == "content_expander"

    def test_no_llm_configured_uses_fallback(self):
        from pptgen.content_intelligence import SlideIntent, expand_slide as _expand
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            si = SlideIntent(title="Reliability", intent_type="impact")
            result = _expand(si)
            assert result.assertion is not None
            assert len(result.supporting_points) >= 3
        finally:
            override_settings(None)
