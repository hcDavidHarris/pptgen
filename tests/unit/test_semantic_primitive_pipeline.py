"""End-to-end tests for semantic primitive integration in the CI pipeline — Phase 11C.

Covers:
- Primitive assignment after narrative building
- Primitive propagation through expansion, insights, critic
- Primitive validation recorded in metadata
- Representative narrative patterns: executive transformation, architecture,
  metrics/performance insight, recommendation
- No pipeline regressions from Phase 11A/11B
- No raw source-object serialization in normalized output
"""

from __future__ import annotations

import pytest

from pptgen.content_intelligence import (
    ContentIntent,
    EnrichedSlideContent,
    SlideIntent,
    run_content_intelligence,
)
from pptgen.content_intelligence.content_intelligence_pipeline import run_content_intelligence
from pptgen.content_intelligence.normalizer import normalize_for_pipeline
from pptgen.content_intelligence.primitive_registry import (
    FALLBACK_PRIMITIVE_NAME,
    list_primitive_names,
)
from pptgen.content_intelligence.primitive_selector import select_primitive


# ---------------------------------------------------------------------------
# Pipeline returns EnrichedSlideContent with primitive assigned
# ---------------------------------------------------------------------------

class TestPipelinePrimitiveAssignment:
    def test_each_slide_has_primitive_set(self):
        intent = ContentIntent(topic="Cloud Migration Strategy")
        slides = run_content_intelligence(intent)
        for slide in slides:
            assert slide.primitive is not None, "Every slide must have a primitive assigned"

    def test_primitive_is_registered(self):
        intent = ContentIntent(topic="Digital Transformation")
        slides = run_content_intelligence(intent)
        registered = set(list_primitive_names())
        for slide in slides:
            assert slide.primitive in registered, (
                f"Slide primitive '{slide.primitive}' is not in the registry"
            )

    def test_pipeline_returns_list_of_enriched_content(self):
        intent = ContentIntent(topic="Operational Efficiency")
        slides = run_content_intelligence(intent)
        assert isinstance(slides, list)
        assert len(slides) >= 1
        for slide in slides:
            assert isinstance(slide, EnrichedSlideContent)


# ---------------------------------------------------------------------------
# Primitive validation recorded in metadata
# ---------------------------------------------------------------------------

class TestPrimitiveValidationMetadata:
    def test_primitive_validation_key_in_metadata(self):
        intent = ContentIntent(topic="Performance Improvement")
        slides = run_content_intelligence(intent)
        for slide in slides:
            assert "primitive_validation" in slide.metadata, (
                "primitive_validation must be recorded in metadata for every slide"
            )

    def test_primitive_validation_has_passed_field(self):
        intent = ContentIntent(topic="Security Posture")
        slides = run_content_intelligence(intent)
        for slide in slides:
            validation = slide.metadata["primitive_validation"]
            assert "passed" in validation
            assert isinstance(validation["passed"], bool)

    def test_primitive_validation_has_violations_field(self):
        intent = ContentIntent(topic="Data Platform")
        slides = run_content_intelligence(intent)
        for slide in slides:
            validation = slide.metadata["primitive_validation"]
            assert "violations" in validation
            assert isinstance(validation["violations"], list)

    def test_primitive_validation_has_primitive_field(self):
        intent = ContentIntent(topic="Infrastructure Modernisation")
        slides = run_content_intelligence(intent)
        for slide in slides:
            validation = slide.metadata["primitive_validation"]
            assert "primitive" in validation
            assert validation["primitive"] in list_primitive_names()


# ---------------------------------------------------------------------------
# Primitive propagates through the normalizer
# ---------------------------------------------------------------------------

class TestNormalizerIntegration:
    def test_normalized_output_has_ci_metadata(self):
        intent = ContentIntent(topic="API Strategy")
        slides = run_content_intelligence(intent)
        for slide in slides:
            normalized = normalize_for_pipeline(slide)
            assert "_ci_metadata" in normalized

    def test_normalized_ci_metadata_contains_primitive(self):
        intent = ContentIntent(topic="Talent Transformation")
        slides = run_content_intelligence(intent)
        for slide in slides:
            normalized = normalize_for_pipeline(slide)
            meta = normalized["_ci_metadata"]
            assert "primitive" in meta
            assert meta["primitive"] in list_primitive_names()

    def test_normalized_top_level_keys_are_correct(self):
        intent = ContentIntent(topic="Cost Optimisation")
        slides = run_content_intelligence(intent)
        expected_keys = {"title", "content", "bullets", "notes", "_ci_metadata"}
        for slide in slides:
            normalized = normalize_for_pipeline(slide)
            assert set(normalized.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Representative narrative patterns
# ---------------------------------------------------------------------------

class TestRepresentativeNarrativePatterns:
    """Verify that the primitive system handles real-world narrative patterns correctly."""

    def test_executive_transformation_proposal(self):
        """Executive transformation: problem → transformation → recommendation pattern."""
        intent = ContentIntent(
            topic="Digital Transformation Programme",
            goal="Secure board approval for a three-year digital transformation investment",
            audience="Executive Leadership Team",
        )
        slides = run_content_intelligence(intent)
        assert len(slides) >= 1
        # All slides must have a primitive
        for slide in slides:
            assert slide.primitive is not None
        # Must produce substantive content
        for slide in slides:
            assert slide.assertion, "Assertion must not be empty"
            assert len(slide.supporting_points) >= 3, (
                "Executive transformation slides require >=3 supporting points"
            )

    def test_architecture_explanation_pattern(self):
        """Architecture explanation: system components, design principles."""
        intent = ContentIntent(
            topic="Event-Driven Microservices Architecture",
            goal="Explain the proposed architecture to the engineering team",
            audience="Senior Engineers",
        )
        slides = run_content_intelligence(intent)
        for slide in slides:
            assert slide.primitive is not None
            assert slide.assertion

    def test_metrics_performance_insight_pattern(self):
        """Metrics insight: measurable outcomes + interpretation."""
        intent = ContentIntent(
            topic="Platform Performance Improvement Results",
            goal="Report Q3 performance outcomes to product leadership",
            audience="Product Leadership",
        )
        slides = run_content_intelligence(intent)
        for slide in slides:
            assert slide.primitive is not None
            assert slide.assertion
            assert len(slide.supporting_points) >= 3

    def test_recommendation_slide_pattern(self):
        """Recommendation: recommended action, rationale, expected outcome."""
        intent = ContentIntent(
            topic="Vendor Selection for Cloud Infrastructure",
            goal="Recommend the preferred vendor to the procurement committee",
            audience="Procurement Committee",
        )
        slides = run_content_intelligence(intent)
        for slide in slides:
            assert slide.primitive is not None
            assert slide.assertion


# ---------------------------------------------------------------------------
# Phase 11A/11B regression tests — existing contracts must hold
# ---------------------------------------------------------------------------

class TestPhase11Regressions:
    def test_run_returns_list(self):
        result = run_content_intelligence(ContentIntent(topic="Test Topic"))
        assert isinstance(result, list)

    def test_each_result_is_enriched_slide_content(self):
        slides = run_content_intelligence(ContentIntent(topic="Test Topic"))
        for s in slides:
            assert isinstance(s, EnrichedSlideContent)

    def test_each_slide_has_title(self):
        slides = run_content_intelligence(ContentIntent(topic="Test Topic"))
        for s in slides:
            assert s.title and s.title.strip()

    def test_each_slide_has_assertion(self):
        slides = run_content_intelligence(ContentIntent(topic="Test Topic"))
        for s in slides:
            assert s.assertion and s.assertion.strip()

    def test_each_slide_has_at_least_three_supporting_points(self):
        slides = run_content_intelligence(ContentIntent(topic="Test Topic"))
        for s in slides:
            assert len(s.supporting_points) >= 3

    def test_pipeline_is_deterministic(self):
        intent = ContentIntent(topic="Determinism Check")
        first_run = run_content_intelligence(intent)
        second_run = run_content_intelligence(intent)
        assert len(first_run) == len(second_run)
        for a, b in zip(first_run, second_run):
            assert a.title == b.title
            assert a.assertion == b.assertion
            assert a.supporting_points == b.supporting_points
            assert a.primitive == b.primitive

    def test_content_intent_optional_fields_accepted(self):
        intent = ContentIntent(
            topic="Minimal Input",
            goal=None,
            audience=None,
            context=None,
        )
        slides = run_content_intelligence(intent)
        assert len(slides) >= 1

    def test_normalized_output_has_no_enriched_content_objects(self):
        intent = ContentIntent(topic="Leakage Check")
        slides = run_content_intelligence(intent)
        for slide in slides:
            normalized = normalize_for_pipeline(slide)
            for key in ("title", "content", "bullets", "notes"):
                assert not isinstance(normalized[key], EnrichedSlideContent), (
                    f"Raw EnrichedSlideContent object leaked into key '{key}'"
                )


# ---------------------------------------------------------------------------
# select_primitive + pipeline consistency
# ---------------------------------------------------------------------------

class TestSelectorPipelineConsistency:
    @pytest.mark.parametrize("intent_type,expected_primitive", [
        ("problem", "problem_statement"),
        ("solution", "recommendation"),
        ("impact", "metrics_with_insight"),
    ])
    def test_fallback_narrative_uses_expected_primitives(self, intent_type, expected_primitive):
        """The fallback narrative produces problem/solution/impact slides.
        Verify these map to the expected semantic primitives."""
        result = select_primitive(intent_type)
        assert result == expected_primitive
