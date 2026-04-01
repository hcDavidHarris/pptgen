"""Tests for primitive-aware normalization — Phase 11C."""

import pytest

from pptgen.content_intelligence.content_models import EnrichedSlideContent
from pptgen.content_intelligence.normalizer import normalize_for_pipeline
from pptgen.content_intelligence.primitive_registry import FALLBACK_PRIMITIVE_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_content(primitive=None, metadata=None, **kwargs) -> EnrichedSlideContent:
    defaults = dict(
        title="Test Slide",
        assertion="The assertion.",
        supporting_points=["P1.", "P2.", "P3."],
        implications=["Implication."],
        metadata=metadata or {},
        primitive=primitive,
    )
    defaults.update(kwargs)
    return EnrichedSlideContent(**defaults)


# ---------------------------------------------------------------------------
# Core contract — pipeline keys must remain stable
# ---------------------------------------------------------------------------

class TestNormalizerPipelineContract:
    def test_title_preserved(self):
        content = _make_content(title="My Slide")
        result = normalize_for_pipeline(content)
        assert result["title"] == "My Slide"

    def test_content_maps_to_assertion(self):
        content = _make_content(assertion="The main point.")
        result = normalize_for_pipeline(content)
        assert result["content"] == "The main point."

    def test_content_empty_string_when_no_assertion(self):
        content = _make_content(assertion=None)
        result = normalize_for_pipeline(content)
        assert result["content"] == ""

    def test_bullets_maps_to_supporting_points(self):
        content = _make_content(supporting_points=["A.", "B."])
        result = normalize_for_pipeline(content)
        assert result["bullets"] == ["A.", "B."]

    def test_notes_maps_to_implications(self):
        content = _make_content(implications=["Implication 1.", "Implication 2."])
        result = normalize_for_pipeline(content)
        assert result["notes"] == "Implication 1.; Implication 2."

    def test_notes_empty_string_when_no_implications(self):
        content = _make_content(implications=None)
        result = normalize_for_pipeline(content)
        assert result["notes"] == ""

    def test_ci_metadata_key_present(self):
        content = _make_content()
        result = normalize_for_pipeline(content)
        assert "_ci_metadata" in result


# ---------------------------------------------------------------------------
# Primitive surfaces in _ci_metadata
# ---------------------------------------------------------------------------

class TestPrimitiveInMetadata:
    def test_primitive_included_in_ci_metadata(self):
        content = _make_content(primitive="recommendation")
        result = normalize_for_pipeline(content)
        assert result["_ci_metadata"]["primitive"] == "recommendation"

    def test_fallback_primitive_included_in_ci_metadata(self):
        content = _make_content(primitive=FALLBACK_PRIMITIVE_NAME)
        result = normalize_for_pipeline(content)
        assert result["_ci_metadata"]["primitive"] == FALLBACK_PRIMITIVE_NAME

    def test_no_primitive_does_not_inject_key(self):
        content = _make_content(primitive=None, metadata={})
        result = normalize_for_pipeline(content)
        # _ci_metadata should not have a "primitive" key when primitive is None
        assert "primitive" not in result["_ci_metadata"]

    def test_primitive_in_both_field_and_metadata(self):
        content = _make_content(
            primitive="roadmap",
            metadata={"primitive": "roadmap", "source": "prompt"},
        )
        result = normalize_for_pipeline(content)
        assert result["_ci_metadata"]["primitive"] == "roadmap"


# ---------------------------------------------------------------------------
# Primitive validation results surface in _ci_metadata
# ---------------------------------------------------------------------------

class TestPrimitiveValidationInMetadata:
    def test_validation_result_preserved_from_metadata(self):
        validation = {
            "passed": True,
            "primitive": "recommendation",
            "violations": [],
        }
        content = _make_content(
            primitive="recommendation",
            metadata={"primitive_validation": validation},
        )
        result = normalize_for_pipeline(content)
        assert result["_ci_metadata"]["primitive_validation"]["passed"] is True
        assert result["_ci_metadata"]["primitive_validation"]["primitive"] == "recommendation"

    def test_failed_validation_preserved_in_metadata(self):
        validation = {
            "passed": False,
            "primitive": "problem_statement",
            "violations": ["[problem_statement] assertion is missing or blank"],
        }
        content = _make_content(
            primitive="problem_statement",
            metadata={"primitive_validation": validation},
        )
        result = normalize_for_pipeline(content)
        meta = result["_ci_metadata"]["primitive_validation"]
        assert meta["passed"] is False
        assert len(meta["violations"]) == 1


# ---------------------------------------------------------------------------
# No raw source object serialization reaches the normalized output
# ---------------------------------------------------------------------------

class TestNoRawSourceObjectLeakage:
    def test_title_is_string_not_object(self):
        content = _make_content(title="Slide Title")
        result = normalize_for_pipeline(content)
        assert isinstance(result["title"], str)

    def test_content_is_string_not_object(self):
        content = _make_content()
        result = normalize_for_pipeline(content)
        assert isinstance(result["content"], str)

    def test_bullets_is_list_of_strings(self):
        content = _make_content(supporting_points=["A.", "B.", "C."])
        result = normalize_for_pipeline(content)
        assert isinstance(result["bullets"], list)
        assert all(isinstance(b, str) for b in result["bullets"])

    def test_notes_is_string(self):
        content = _make_content(implications=["Impl 1."])
        result = normalize_for_pipeline(content)
        assert isinstance(result["notes"], str)

    def test_enriched_content_object_not_in_output(self):
        content = _make_content()
        result = normalize_for_pipeline(content)
        for key in ("title", "content", "bullets", "notes"):
            assert not isinstance(result[key], EnrichedSlideContent)

    def test_no_to_dict_artifacts_in_top_level(self):
        """Top-level keys should only be the expected pipeline keys."""
        content = _make_content()
        result = normalize_for_pipeline(content)
        expected_keys = {"title", "content", "bullets", "notes", "_ci_metadata"}
        assert set(result.keys()) == expected_keys

    def test_metadata_dict_is_copied_not_mutated(self):
        original_meta = {"source": "prompt"}
        content = _make_content(primitive="roadmap", metadata=original_meta)
        normalize_for_pipeline(content)
        # The original metadata dict must not be mutated
        assert "primitive" not in original_meta
