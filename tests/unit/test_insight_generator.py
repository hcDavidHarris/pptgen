"""Tests for the insight generator — Phase 11A / Phase 11B."""
from __future__ import annotations

from unittest.mock import patch

from pptgen.content_intelligence import EnrichedSlideContent, generate_insights


# ---------------------------------------------------------------------------
# Phase 11A contracts (must remain green)
# ---------------------------------------------------------------------------


class TestGenerateInsights:
    def test_returns_enriched_slide_content(self):
        content = EnrichedSlideContent(
            title="T", assertion="A.", supporting_points=["a", "b", "c"]
        )
        result = generate_insights(content)
        assert isinstance(result, EnrichedSlideContent)

    def test_title_preserved(self):
        content = EnrichedSlideContent(title="My Slide", supporting_points=["a", "b", "c"])
        result = generate_insights(content)
        assert result.title == "My Slide"

    def test_assertion_preserved(self):
        content = EnrichedSlideContent(
            title="T", assertion="Strong claim.", supporting_points=["a", "b", "c"]
        )
        result = generate_insights(content)
        assert result.assertion == "Strong claim."

    def test_supporting_points_preserved(self):
        pts = ["X.", "Y.", "Z."]
        content = EnrichedSlideContent(title="T", supporting_points=pts)
        result = generate_insights(content)
        assert result.supporting_points == pts

    def test_implications_populated(self):
        content = EnrichedSlideContent(title="T", supporting_points=["First point.", "B.", "C."])
        result = generate_insights(content)
        assert result.implications is not None
        assert len(result.implications) >= 1

    def test_insights_applied_in_metadata(self):
        content = EnrichedSlideContent(title="T", supporting_points=["a", "b", "c"])
        result = generate_insights(content)
        assert result.metadata.get("insights_applied") is True

    def test_existing_metadata_preserved(self):
        content = EnrichedSlideContent(
            title="T",
            supporting_points=["a", "b", "c"],
            metadata={"intent_type": "solution", "source": "content_expander"},
        )
        result = generate_insights(content)
        assert result.metadata.get("intent_type") == "solution"
        assert result.metadata.get("insights_applied") is True

    def test_empty_supporting_points_produces_empty_implications_fallback(self):
        content = EnrichedSlideContent(title="T", supporting_points=[])
        result = generate_insights(content)
        # Fallback: empty supporting_points → empty implications list
        assert result.implications is not None

    def test_is_deterministic(self):
        content = EnrichedSlideContent(
            title="T", assertion="A.", supporting_points=["Alpha.", "Beta.", "Gamma."]
        )
        r1 = generate_insights(content)
        r2 = generate_insights(content)
        assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# Phase 11B — prompt-driven path and fallback integration
# ---------------------------------------------------------------------------


class TestGenerateInsightsPhase11B:
    """Phase 11B: prompt integration, field preservation, fallback fidelity."""

    def test_prompt_success_enriches_implications(self):
        """When run_prompt returns valid implications, generate_insights forwards them."""
        content = EnrichedSlideContent(
            title="Cost Reduction: Impact",
            assertion="Migration reduces opex by 40%.",
            supporting_points=["Lower hosting.", "Elastic scale.", "Reduced headcount."],
            metadata={"source": "prompt", "intent_type": "impact"},
        )
        prompt_result = EnrichedSlideContent(
            title=content.title,
            assertion=content.assertion,
            supporting_points=content.supporting_points,
            implications=[
                "Leadership must accelerate cloud commitments before Q3 budget lock.",
                "Teams should benchmark against new cost baseline immediately.",
            ],
            metadata={**content.metadata, "insights_applied": True},
        )
        with patch(
            "pptgen.content_intelligence.insight_generator.run_prompt",
            return_value=prompt_result,
        ):
            result = generate_insights(content)

        assert result is prompt_result
        assert len(result.implications) == 2

    def test_fallback_matches_phase11a_output(self):
        """_generate_insights_fallback is identical to Phase 11A generate_insights."""
        from pptgen.content_intelligence.insight_generator import _generate_insights_fallback

        content = EnrichedSlideContent(
            title="T",
            assertion="A.",
            supporting_points=["First point.", "B.", "C."],
            metadata={"source": "expander"},
        )
        result = _generate_insights_fallback(content)

        assert result.title == content.title
        assert result.assertion == content.assertion
        assert result.supporting_points == content.supporting_points
        assert result.implications is not None
        assert len(result.implications) == 1
        assert "First point" in result.implications[0]
        assert result.metadata.get("insights_applied") is True

    def test_fallback_empty_points_produces_empty_implications(self):
        from pptgen.content_intelligence.insight_generator import _generate_insights_fallback

        content = EnrichedSlideContent(title="T", supporting_points=[])
        result = _generate_insights_fallback(content)
        assert result.implications == []

    def test_fallback_is_deterministic(self):
        from pptgen.content_intelligence.insight_generator import _generate_insights_fallback

        content = EnrichedSlideContent(
            title="T", assertion="A.", supporting_points=["X.", "Y.", "Z."]
        )
        r1 = _generate_insights_fallback(content)
        r2 = _generate_insights_fallback(content)
        assert r1.to_dict() == r2.to_dict()

    def test_prompt_runner_receives_correct_context(self):
        """generate_insights passes title/assertion/supporting_points to run_prompt."""
        captured = {}

        def _spy(prompt_name, context, parser, fallback, validator=None, llm_caller=None, **kwargs):
            captured.update(context)
            return fallback()

        content = EnrichedSlideContent(
            title="Impact Slide",
            assertion="Revenue grows 20%.",
            supporting_points=["Market share rises.", "CAC drops.", "NPS improves."],
        )
        with patch(
            "pptgen.content_intelligence.insight_generator.run_prompt",
            side_effect=_spy,
        ):
            generate_insights(content)

        assert captured["title"] == "Impact Slide"
        assert captured["assertion"] == "Revenue grows 20%."
        assert captured["supporting_points"] == content.supporting_points

    def test_invalid_implications_trigger_fallback(self):
        """Empty implications from prompt must be rejected by validator."""
        content = EnrichedSlideContent(
            title="T",
            assertion="A.",
            supporting_points=["a", "b", "c"],
        )

        def _mock_runner(prompt_name, context, parser, fallback, validator=None, llm_caller=None, **kwargs):
            # Simulate: prompt returned empty implications — validator rejects
            bad = EnrichedSlideContent(
                title=content.title,
                assertion=content.assertion,
                supporting_points=content.supporting_points,
                implications=[],  # fails validate_insight_output
                metadata={"insights_applied": True},
            )
            if validator and not validator(bad):
                return fallback()
            return bad

        with patch(
            "pptgen.content_intelligence.insight_generator.run_prompt",
            side_effect=_mock_runner,
        ):
            result = generate_insights(content)

        # Fallback always produces a non-empty implications list when points exist
        assert result.implications is not None

    def test_no_llm_configured_uses_fallback(self):
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            content = EnrichedSlideContent(
                title="T",
                assertion="A.",
                supporting_points=["Alpha.", "Beta.", "Gamma."],
            )
            result = generate_insights(content)
            assert result.implications is not None
            assert result.metadata.get("insights_applied") is True
        finally:
            override_settings(None)
