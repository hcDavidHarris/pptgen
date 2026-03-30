"""Tests for the narrative builder — Phase 11A / Phase 11B."""

from __future__ import annotations

from unittest.mock import patch

from pptgen.content_intelligence import ContentIntent, SlideIntent, build_narrative


class TestBuildNarrative:
    def test_returns_three_slides(self):
        ci = ContentIntent(topic="Data Platform")
        slides = build_narrative(ci)
        assert len(slides) == 3

    def test_slide_types_are_correct(self):
        ci = ContentIntent(topic="Security Posture")
        slides = build_narrative(ci)
        intent_types = [s.intent_type for s in slides]
        assert intent_types == ["problem", "solution", "impact"]

    def test_titles_embed_topic(self):
        ci = ContentIntent(topic="Cloud Migration")
        slides = build_narrative(ci)
        for slide in slides:
            assert "Cloud Migration" in slide.title

    def test_each_slide_has_key_points(self):
        ci = ContentIntent(topic="DevOps")
        slides = build_narrative(ci)
        for slide in slides:
            assert len(slide.key_points) >= 1

    def test_returns_slide_intent_instances(self):
        ci = ContentIntent(topic="AI")
        slides = build_narrative(ci)
        assert all(isinstance(s, SlideIntent) for s in slides)

    def test_is_deterministic(self):
        ci = ContentIntent(topic="Platform")
        first = build_narrative(ci)
        second = build_narrative(ci)
        assert [s.to_dict() for s in first] == [s.to_dict() for s in second]

    def test_different_topics_produce_different_slides(self):
        slides_a = build_narrative(ContentIntent(topic="Topic A"))
        slides_b = build_narrative(ContentIntent(topic="Topic B"))
        assert slides_a[0].title != slides_b[0].title

    def test_goal_and_audience_do_not_break_output(self):
        ci = ContentIntent(topic="Infra", goal="Reduce costs", audience="CTO")
        slides = build_narrative(ci)
        assert len(slides) == 3


# ---------------------------------------------------------------------------
# Phase 11B — prompt-driven path and fallback integration
# ---------------------------------------------------------------------------


class TestBuildNarrativePhase11B:
    """Phase 11B: prompt integration, fallback fidelity, validator behaviour."""

    def test_prompt_success_propagates_richer_slides(self):
        """When run_prompt returns valid SlideIntents, build_narrative forwards them."""
        rich_slides = [
            SlideIntent(
                title="Cloud Migration: The Hidden Costs",
                intent_type="problem",
                key_points=["Legacy spend is 3x cloud.", "Scale ceilings hit quarterly."],
            ),
            SlideIntent(
                title="Cloud Migration: A Phased Lift-and-Shift",
                intent_type="solution",
                key_points=["Workloads grouped by criticality.", "Zero-downtime migration."],
            ),
        ]
        with patch(
            "pptgen.content_intelligence.narrative_builder.run_prompt",
            return_value=rich_slides,
        ):
            result = build_narrative(ContentIntent(topic="Cloud Migration"))

        assert result is rich_slides

    def test_fallback_matches_phase11a_structure(self):
        """_narrative_fallback output is identical to Phase 11A implementation."""
        from pptgen.content_intelligence.narrative_builder import _narrative_fallback

        ci = ContentIntent(topic="Platform Engineering")
        result = _narrative_fallback(ci)

        assert len(result) == 3
        assert [s.intent_type for s in result] == ["problem", "solution", "impact"]
        for slide in result:
            assert "Platform Engineering" in slide.title
            assert len(slide.key_points) >= 1

    def test_fallback_is_deterministic(self):
        from pptgen.content_intelligence.narrative_builder import _narrative_fallback

        ci = ContentIntent(topic="Reliability")
        first = _narrative_fallback(ci)
        second = _narrative_fallback(ci)
        assert [s.to_dict() for s in first] == [s.to_dict() for s in second]

    def test_no_llm_configured_uses_fallback_path(self):
        """With mock provider (no API key), run_prompt falls back deterministically."""
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            ci = ContentIntent(topic="DevSecOps")
            result = build_narrative(ci)
            assert len(result) >= 1
            assert all(isinstance(s, SlideIntent) for s in result)
            for slide in result:
                assert slide.title and slide.intent_type
                assert len(slide.key_points) >= 1
        finally:
            override_settings(None)

    def test_prompt_runner_receives_correct_context(self):
        """build_narrative passes topic/goal/audience to run_prompt context."""
        captured = {}

        def _spy(prompt_name, context, parser, fallback, validator=None, llm_caller=None, **kwargs):
            captured.update(context)
            return fallback()

        with patch(
            "pptgen.content_intelligence.narrative_builder.run_prompt",
            side_effect=_spy,
        ):
            build_narrative(ContentIntent(topic="AI Strategy", goal="Cut costs", audience="Board"))

        assert captured["topic"] == "AI Strategy"
        assert captured["goal"] == "Cut costs"
        assert captured["audience"] == "Board"
