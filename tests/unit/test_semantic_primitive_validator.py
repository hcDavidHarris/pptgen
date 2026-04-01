"""Tests for primitive-aware content validation — Phase 11C."""

import pytest

from pptgen.content_intelligence.content_models import EnrichedSlideContent
from pptgen.content_intelligence.primitive_registry import FALLBACK_PRIMITIVE_NAME
from pptgen.content_intelligence.primitive_validator import (
    PrimitiveValidationResult,
    validate_primitive_content,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_content(
    title="Test Slide",
    assertion="The assertion.",
    supporting_points=None,
    implications=None,
    primitive=None,
) -> EnrichedSlideContent:
    return EnrichedSlideContent(
        title=title,
        assertion=assertion,
        supporting_points=supporting_points or [],
        implications=implications,
        primitive=primitive,
    )


# ---------------------------------------------------------------------------
# PrimitiveValidationResult contract
# ---------------------------------------------------------------------------

class TestPrimitiveValidationResult:
    def test_passed_true_has_empty_violations(self):
        result = PrimitiveValidationResult(
            passed=True, primitive_name="recommendation", violations=()
        )
        assert result.violations == ()

    def test_passed_false_has_violations(self):
        result = PrimitiveValidationResult(
            passed=False, primitive_name="problem_statement", violations=("missing assertion",)
        )
        assert len(result.violations) == 1

    def test_is_frozen(self):
        result = PrimitiveValidationResult(passed=True, primitive_name="roadmap", violations=())
        with pytest.raises((AttributeError, TypeError)):
            result.passed = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# problem_statement — requires 3 supporting_points + 1 implication
# ---------------------------------------------------------------------------

class TestProblemStatementValidation:
    def test_valid_passes(self):
        content = _make_content(
            assertion="Legacy systems are creating critical bottlenecks.",
            supporting_points=[
                "95% of manual processes lack automation.",
                "Average resolution time is 3x industry benchmark.",
                "Downtime incidents increased 40% YoY.",
            ],
            implications=["Without intervention, capacity will be exceeded by Q3."],
        )
        result = validate_primitive_content(content, "problem_statement")
        assert result.passed is True
        assert result.violations == ()

    def test_missing_assertion_fails(self):
        content = _make_content(
            assertion="",
            supporting_points=["Point 1.", "Point 2.", "Point 3."],
            implications=["Implication."],
        )
        result = validate_primitive_content(content, "problem_statement")
        assert result.passed is False
        assert any("assertion" in v for v in result.violations)

    def test_too_few_supporting_points_fails(self):
        content = _make_content(
            assertion="There is a problem.",
            supporting_points=["Only one point."],
            implications=["Consequence."],
        )
        result = validate_primitive_content(content, "problem_statement")
        assert result.passed is False
        assert any("supporting" in v for v in result.violations)

    def test_missing_implications_fails(self):
        content = _make_content(
            assertion="There is a problem.",
            supporting_points=["Point 1.", "Point 2.", "Point 3."],
            implications=None,
        )
        result = validate_primitive_content(content, "problem_statement")
        assert result.passed is False
        assert any("implication" in v for v in result.violations)

    def test_empty_implications_list_fails(self):
        content = _make_content(
            assertion="There is a problem.",
            supporting_points=["Point 1.", "Point 2.", "Point 3."],
            implications=[],
        )
        result = validate_primitive_content(content, "problem_statement")
        assert result.passed is False


# ---------------------------------------------------------------------------
# metrics_with_insight — requires 2 supporting_points + 1 implication
# ---------------------------------------------------------------------------

class TestMetricsWithInsightValidation:
    def test_valid_passes(self):
        content = _make_content(
            assertion="Platform performance has improved by 60% this quarter.",
            supporting_points=[
                "P99 latency dropped from 800ms to 320ms.",
                "Error rate fell from 2.1% to 0.3%.",
            ],
            implications=["The system can now handle 3x peak load without degradation."],
        )
        result = validate_primitive_content(content, "metrics_with_insight")
        assert result.passed is True

    def test_no_implications_fails(self):
        content = _make_content(
            assertion="Performance improved.",
            supporting_points=["Latency down.", "Errors down."],
            implications=[],
        )
        result = validate_primitive_content(content, "metrics_with_insight")
        assert result.passed is False

    def test_one_supporting_point_fails(self):
        content = _make_content(
            assertion="Performance improved.",
            supporting_points=["Only one metric."],
            implications=["This matters."],
        )
        result = validate_primitive_content(content, "metrics_with_insight")
        assert result.passed is False


# ---------------------------------------------------------------------------
# recommendation — requires 2 supporting_points + 1 implication
# ---------------------------------------------------------------------------

class TestRecommendationValidation:
    def test_valid_passes(self):
        content = _make_content(
            assertion="Migrate the data pipeline to the cloud-native architecture.",
            supporting_points=[
                "Current on-prem infrastructure cannot scale to meet demand.",
                "Cloud-native reduces operational overhead by an estimated 35%.",
            ],
            implications=["Teams can redirect 2 FTEs to product development within 6 months."],
        )
        result = validate_primitive_content(content, "recommendation")
        assert result.passed is True

    def test_no_rationale_fails(self):
        content = _make_content(
            assertion="Do the thing.",
            supporting_points=["One reason."],
            implications=["Expected benefit."],
        )
        result = validate_primitive_content(content, "recommendation")
        assert result.passed is False

    def test_no_outcome_fails(self):
        content = _make_content(
            assertion="Do the thing.",
            supporting_points=["Reason 1.", "Reason 2."],
            implications=None,
        )
        result = validate_primitive_content(content, "recommendation")
        assert result.passed is False


# ---------------------------------------------------------------------------
# before_after_transformation — requires 4 supporting_points
# ---------------------------------------------------------------------------

class TestBeforeAfterTransformationValidation:
    def test_valid_passes(self):
        content = _make_content(
            assertion="The organisation is moving from reactive to proactive operations.",
            supporting_points=[
                "Before: Incidents detected by end users.",
                "Before: Resolution time averages 6 hours.",
                "After: 90% of incidents auto-detected before user impact.",
                "After: Mean time to resolve drops to 45 minutes.",
            ],
        )
        result = validate_primitive_content(content, "before_after_transformation")
        assert result.passed is True

    def test_three_supporting_points_fails(self):
        content = _make_content(
            assertion="Transformation.",
            supporting_points=["Before 1.", "Before 2.", "After 1."],
        )
        result = validate_primitive_content(content, "before_after_transformation")
        assert result.passed is False


# ---------------------------------------------------------------------------
# Primitives that do NOT require implications
# ---------------------------------------------------------------------------

class TestNonImplicationPrimitives:
    @pytest.mark.parametrize("primitive_name,min_points", [
        ("why_it_matters", 2),
        ("before_after_transformation", 4),
        ("capability_maturity", 2),
        ("architecture_explanation", 3),
        ("decision_framework", 2),
        ("roadmap", 2),
        ("risk_and_mitigation", 2),
    ])
    def test_passes_without_implications_when_sufficient_points(self, primitive_name, min_points):
        content = _make_content(
            assertion="This is the assertion.",
            supporting_points=[f"Point {i+1}." for i in range(min_points)],
            implications=None,
        )
        result = validate_primitive_content(content, primitive_name)
        assert result.passed is True, (
            f"{primitive_name} should pass with {min_points} points and no implications"
        )


# ---------------------------------------------------------------------------
# Fallback primitive
# ---------------------------------------------------------------------------

class TestFallbackPrimitiveValidation:
    def test_valid_passes(self):
        content = _make_content(
            assertion="Summary of the topic.",
            supporting_points=["Point 1.", "Point 2.", "Point 3."],
        )
        result = validate_primitive_content(content, FALLBACK_PRIMITIVE_NAME)
        assert result.passed is True

    def test_two_points_fails(self):
        content = _make_content(
            assertion="Summary.",
            supporting_points=["Point 1.", "Point 2."],
        )
        result = validate_primitive_content(content, FALLBACK_PRIMITIVE_NAME)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Unknown primitive name — graceful fallback to fallback rules
# ---------------------------------------------------------------------------

class TestUnknownPrimitiveName:
    def test_unknown_primitive_falls_back_gracefully(self):
        content = _make_content(
            assertion="Some assertion.",
            supporting_points=["A.", "B.", "C."],
        )
        result = validate_primitive_content(content, "nonexistent_primitive_xyz")
        # Result must be a valid result object with fallback primitive name
        assert isinstance(result, PrimitiveValidationResult)
        assert result.primitive_name == FALLBACK_PRIMITIVE_NAME

    def test_unknown_primitive_valid_content_passes(self):
        content = _make_content(
            assertion="Valid assertion.",
            supporting_points=["A.", "B.", "C."],
        )
        result = validate_primitive_content(content, "no_such_primitive")
        assert result.passed is True


# ---------------------------------------------------------------------------
# Violation message quality
# ---------------------------------------------------------------------------

class TestViolationMessages:
    def test_violations_include_primitive_name(self):
        content = _make_content(assertion="", supporting_points=[], implications=None)
        result = validate_primitive_content(content, "problem_statement")
        assert all("problem_statement" in v for v in result.violations)

    def test_multiple_violations_reported(self):
        content = _make_content(assertion="", supporting_points=[], implications=None)
        result = validate_primitive_content(content, "recommendation")
        # Missing assertion + insufficient points + no implication → 3 violations
        assert len(result.violations) >= 2

    def test_violations_are_strings(self):
        content = _make_content(assertion="", supporting_points=[])
        result = validate_primitive_content(content, "roadmap")
        assert all(isinstance(v, str) for v in result.violations)
