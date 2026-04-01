"""Tests for the semantic primitive selector — Phase 11C."""

import pytest

from pptgen.content_intelligence.primitive_registry import (
    FALLBACK_PRIMITIVE_NAME,
    list_primitive_names,
)
from pptgen.content_intelligence.primitive_selector import select_primitive


# ---------------------------------------------------------------------------
# Explicit mappings — representative coverage
# ---------------------------------------------------------------------------

class TestExplicitMappings:
    @pytest.mark.parametrize("intent_type,expected", [
        ("problem", "problem_statement"),
        ("challenge", "problem_statement"),
        ("gap", "problem_statement"),
        ("pain", "problem_statement"),
        ("context", "why_it_matters"),
        ("background", "why_it_matters"),
        ("motivation", "why_it_matters"),
        ("why", "why_it_matters"),
        ("transformation", "before_after_transformation"),
        ("change", "before_after_transformation"),
        ("transition", "before_after_transformation"),
        ("metrics", "metrics_with_insight"),
        ("impact", "metrics_with_insight"),
        ("performance", "metrics_with_insight"),
        ("results", "metrics_with_insight"),
        ("data", "metrics_with_insight"),
        ("maturity", "capability_maturity"),
        ("capability", "capability_maturity"),
        ("readiness", "capability_maturity"),
        ("architecture", "architecture_explanation"),
        ("technical", "architecture_explanation"),
        ("system", "architecture_explanation"),
        ("design", "architecture_explanation"),
        ("recommendation", "recommendation"),
        ("action", "recommendation"),
        ("next_steps", "recommendation"),
        ("solution", "recommendation"),
        ("decision", "decision_framework"),
        ("options", "decision_framework"),
        ("tradeoffs", "decision_framework"),
        ("criteria", "decision_framework"),
        ("roadmap", "roadmap"),
        ("plan", "roadmap"),
        ("timeline", "roadmap"),
        ("phases", "roadmap"),
        ("milestones", "roadmap"),
        ("risk", "risk_and_mitigation"),
        ("mitigation", "risk_and_mitigation"),
        ("concerns", "risk_and_mitigation"),
        ("threats", "risk_and_mitigation"),
        ("summary", FALLBACK_PRIMITIVE_NAME),
        ("overview", FALLBACK_PRIMITIVE_NAME),
        ("introduction", FALLBACK_PRIMITIVE_NAME),
        ("conclusion", FALLBACK_PRIMITIVE_NAME),
    ])
    def test_explicit_mapping(self, intent_type, expected):
        assert select_primitive(intent_type) == expected


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------

class TestFallbackBehaviour:
    def test_unknown_intent_type_returns_fallback(self):
        assert select_primitive("completely_unknown_type") == FALLBACK_PRIMITIVE_NAME

    def test_empty_string_returns_fallback(self):
        assert select_primitive("") == FALLBACK_PRIMITIVE_NAME

    def test_blank_string_returns_fallback(self):
        assert select_primitive("   ") == FALLBACK_PRIMITIVE_NAME

    def test_fallback_is_never_empty(self):
        assert FALLBACK_PRIMITIVE_NAME  # not empty string

    def test_fallback_is_registered_primitive(self):
        assert FALLBACK_PRIMITIVE_NAME in list_primitive_names()


# ---------------------------------------------------------------------------
# Normalisation — input handling
# ---------------------------------------------------------------------------

class TestInputNormalisation:
    def test_uppercase_input_normalised(self):
        assert select_primitive("PROBLEM") == "problem_statement"

    def test_mixed_case_input_normalised(self):
        assert select_primitive("Recommendation") == "recommendation"

    def test_leading_trailing_whitespace_stripped(self):
        assert select_primitive("  risk  ") == "risk_and_mitigation"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    @pytest.mark.parametrize("intent_type", [
        "problem", "metrics", "recommendation", "roadmap", "risk", "unknown_x"
    ])
    def test_same_input_always_returns_same_result(self, intent_type):
        results = {select_primitive(intent_type) for _ in range(10)}
        assert len(results) == 1, "select_primitive is not deterministic"


# ---------------------------------------------------------------------------
# All return values are registered primitives
# ---------------------------------------------------------------------------

class TestReturnValuesAreRegistered:
    @pytest.mark.parametrize("intent_type", [
        "problem", "context", "transformation", "metrics", "maturity",
        "architecture", "recommendation", "decision", "roadmap", "risk",
        "summary", "totally_unknown",
    ])
    def test_result_is_always_a_registered_primitive(self, intent_type):
        result = select_primitive(intent_type)
        assert result in list_primitive_names(), (
            f"select_primitive('{intent_type}') returned unregistered primitive '{result}'"
        )
