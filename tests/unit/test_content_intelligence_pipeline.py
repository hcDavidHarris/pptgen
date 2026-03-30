"""Tests for the content intelligence pipeline — Phase 11A."""

from __future__ import annotations

import pytest

from pptgen.content_intelligence import (
    ContentIntent,
    EnrichedSlideContent,
    run_content_intelligence,
)


# ---------------------------------------------------------------------------
# run_content_intelligence orchestration
# ---------------------------------------------------------------------------


class TestRunContentIntelligence:
    def test_returns_list(self):
        ci = ContentIntent(topic="Data Platform")
        result = run_content_intelligence(ci)
        assert isinstance(result, list)

    def test_returns_enriched_slide_content_instances(self):
        ci = ContentIntent(topic="Security")
        result = run_content_intelligence(ci)
        assert all(isinstance(s, EnrichedSlideContent) for s in result)

    def test_produces_three_slides_by_default(self):
        ci = ContentIntent(topic="Cloud Migration")
        result = run_content_intelligence(ci)
        assert len(result) == 3

    def test_all_slides_have_non_empty_title(self):
        ci = ContentIntent(topic="Infra Modernisation")
        result = run_content_intelligence(ci)
        for slide in result:
            assert slide.title and len(slide.title) > 0

    def test_all_slides_have_assertion(self):
        ci = ContentIntent(topic="Cost Reduction")
        result = run_content_intelligence(ci)
        for slide in result:
            assert slide.assertion is not None
            assert len(slide.assertion) > 0

    def test_all_slides_have_minimum_three_supporting_points(self):
        ci = ContentIntent(topic="DevSecOps")
        result = run_content_intelligence(ci)
        for slide in result:
            assert len(slide.supporting_points) >= 3

    def test_all_slides_have_implications(self):
        ci = ContentIntent(topic="API Gateway")
        result = run_content_intelligence(ci)
        for slide in result:
            assert slide.implications is not None

    def test_is_deterministic(self):
        ci = ContentIntent(topic="Platform Engineering")
        first = run_content_intelligence(ci)
        second = run_content_intelligence(ci)
        assert [s.to_dict() for s in first] == [s.to_dict() for s in second]

    def test_all_slides_serializable(self):
        import json
        ci = ContentIntent(topic="Observability")
        result = run_content_intelligence(ci)
        for slide in result:
            json.dumps(slide.to_dict())  # must not raise

    def test_metadata_tracks_all_stages(self):
        ci = ContentIntent(topic="AI Platform")
        result = run_content_intelligence(ci)
        for slide in result:
            # critic_applied is last stage — its presence confirms critic ran
            assert slide.metadata.get("critic_applied") is True
            # insights_applied confirms insight_generator ran
            assert slide.metadata.get("insights_applied") is True

    def test_topic_appears_in_slide_titles(self):
        ci = ContentIntent(topic="XYZ_UNIQUE_TOPIC")
        result = run_content_intelligence(ci)
        for slide in result:
            assert "XYZ_UNIQUE_TOPIC" in slide.title

    def test_with_optional_fields(self):
        ci = ContentIntent(
            topic="Reliability",
            goal="Reduce MTTR",
            audience="SRE team",
            context={"region": "us-east-1"},
        )
        result = run_content_intelligence(ci)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Pipeline integration — generate_presentation accepts content_intent
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    """Verify that generate_presentation wires content_intelligence non-breakingly."""

    def _make_minimal_input(self) -> str:
        """A minimal structured deck YAML that bypasses narrative path."""
        return (
            "slides:\n"
            "  - type: title\n"
            "    title: Test Slide\n"
        )

    def test_pipeline_works_without_content_intent(self):
        from pptgen.pipeline import generate_presentation

        result = generate_presentation(self._make_minimal_input())
        assert result.stage == "deck_planned"
        assert result.enriched_content is None

    def test_pipeline_stores_enriched_content_when_provided(self):
        from pptgen.pipeline import generate_presentation

        ci = ContentIntent(topic="Platform Reliability")
        result = generate_presentation(self._make_minimal_input(), content_intent=ci)
        assert result.stage == "deck_planned"
        assert result.enriched_content is not None
        assert len(result.enriched_content) == 3

    def test_pipeline_enriched_content_matches_direct_call(self):
        from pptgen.pipeline import generate_presentation

        ci = ContentIntent(topic="Observability Stack")
        result = generate_presentation(self._make_minimal_input(), content_intent=ci)
        direct = run_content_intelligence(ci)
        assert [s.to_dict() for s in result.enriched_content] == [
            s.to_dict() for s in direct
        ]

    def test_existing_pipeline_signature_unchanged(self):
        """generate_presentation() signature is backward-compatible."""
        import inspect
        from pptgen.pipeline import generate_presentation

        sig = inspect.signature(generate_presentation)
        # content_intent must be optional (has a default)
        param = sig.parameters.get("content_intent")
        assert param is not None
        assert param.default is None
