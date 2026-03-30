"""Tests for the content intelligence semantic primitive registry — Phase 11C."""

import pytest

from pptgen.content_intelligence.primitive_models import SemanticPrimitiveDefinition
from pptgen.content_intelligence.primitive_registry import (
    FALLBACK_PRIMITIVE_NAME,
    get_all_primitives,
    get_primitive,
    list_primitive_names,
)

EXPECTED_SEMANTIC_PRIMITIVES = [
    "problem_statement",
    "why_it_matters",
    "before_after_transformation",
    "metrics_with_insight",
    "capability_maturity",
    "architecture_explanation",
    "recommendation",
    "decision_framework",
    "roadmap",
    "risk_and_mitigation",
    "key_points_summary",
]


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------

class TestRegistryCompleteness:
    def test_all_expected_primitives_registered(self):
        names = list_primitive_names()
        for expected in EXPECTED_SEMANTIC_PRIMITIVES:
            assert expected in names, f"Missing semantic primitive: {expected}"

    def test_primitive_count_stays_focused(self):
        names = list_primitive_names()
        assert 8 <= len(names) <= 15, f"Count out of expected range: {len(names)}"

    def test_fallback_primitive_is_registered(self):
        assert FALLBACK_PRIMITIVE_NAME in list_primitive_names()

    def test_fallback_primitive_name_is_key_points_summary(self):
        assert FALLBACK_PRIMITIVE_NAME == "key_points_summary"

    def test_get_all_primitives_count_matches_list_names(self):
        assert len(get_all_primitives()) == len(list_primitive_names())

    def test_get_all_primitives_order_matches_list_names(self):
        names = list_primitive_names()
        all_prims = get_all_primitives()
        assert [p.name for p in all_prims] == names


# ---------------------------------------------------------------------------
# Definition contract — each primitive must satisfy the model contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", EXPECTED_SEMANTIC_PRIMITIVES)
class TestPrimitiveDefinitionContract:
    def test_returns_correct_type(self, name):
        assert isinstance(get_primitive(name), SemanticPrimitiveDefinition)

    def test_name_matches_key(self, name):
        assert get_primitive(name).name == name

    def test_description_is_non_empty(self, name):
        prim = get_primitive(name)
        assert prim.description and prim.description.strip()

    def test_minimum_supporting_points_at_least_one(self, name):
        assert get_primitive(name).minimum_supporting_points >= 1

    def test_allowed_intent_types_non_empty(self, name):
        prim = get_primitive(name)
        assert len(prim.allowed_intent_types) >= 1

    def test_validation_notes_non_empty(self, name):
        assert len(get_primitive(name).validation_notes) >= 1

    def test_normalization_hint_non_empty(self, name):
        prim = get_primitive(name)
        assert prim.normalization_hint and prim.normalization_hint.strip()

    def test_requires_implications_consistent_with_minimum(self, name):
        prim = get_primitive(name)
        if prim.requires_implications:
            assert prim.minimum_implications >= 1
        else:
            assert prim.minimum_implications >= 0


# ---------------------------------------------------------------------------
# Semantic primitives: specific content-depth requirements
# ---------------------------------------------------------------------------

class TestSemanticPrimitiveDepthRequirements:
    def test_problem_statement_requires_3_supporting_points(self):
        assert get_primitive("problem_statement").minimum_supporting_points >= 3

    def test_problem_statement_requires_implications(self):
        prim = get_primitive("problem_statement")
        assert prim.requires_implications is True
        assert prim.minimum_implications >= 1

    def test_metrics_with_insight_requires_implications(self):
        prim = get_primitive("metrics_with_insight")
        assert prim.requires_implications is True
        assert prim.minimum_implications >= 1

    def test_recommendation_requires_implications(self):
        prim = get_primitive("recommendation")
        assert prim.requires_implications is True
        assert prim.minimum_implications >= 1

    def test_before_after_transformation_requires_4_supporting_points(self):
        assert get_primitive("before_after_transformation").minimum_supporting_points >= 4

    def test_architecture_explanation_requires_3_supporting_points(self):
        assert get_primitive("architecture_explanation").minimum_supporting_points >= 3

    def test_fallback_requires_3_supporting_points(self):
        assert get_primitive(FALLBACK_PRIMITIVE_NAME).minimum_supporting_points >= 3

    def test_fallback_does_not_require_implications(self):
        assert get_primitive(FALLBACK_PRIMITIVE_NAME).requires_implications is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestRegistryErrors:
    def test_unknown_name_raises_key_error(self):
        with pytest.raises(KeyError):
            get_primitive("nonexistent_semantic_primitive")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_primitive_definition_is_frozen(self):
        prim = get_primitive("problem_statement")
        with pytest.raises((AttributeError, TypeError)):
            prim.name = "modified"  # type: ignore[misc]

    def test_allowed_intent_types_is_tuple(self):
        prim = get_primitive("problem_statement")
        assert isinstance(prim.allowed_intent_types, tuple)

    def test_validation_notes_is_tuple(self):
        prim = get_primitive("recommendation")
        assert isinstance(prim.validation_notes, tuple)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_get_primitive_returns_same_object(self):
        assert get_primitive("roadmap") is get_primitive("roadmap")

    def test_list_primitive_names_is_stable(self):
        assert list_primitive_names() == list_primitive_names()

    def test_get_all_primitives_order_is_stable(self):
        first = [p.name for p in get_all_primitives()]
        second = [p.name for p in get_all_primitives()]
        assert first == second
