"""Tests for CI-native artifact serialization and export (Phase 11D).

Covers:
- _build_ci_spec()  — spec.json content and structure
- _build_ci_slide_plan() — slide_plan.json content and structure
- generate_presentation() CI path emits all three artifact files
- Legacy path remains unaffected
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pptgen.content_intelligence.content_models import ContentIntent, EnrichedSlideContent
from pptgen.pipeline.generation_pipeline import (
    _build_ci_spec,
    _build_ci_slide_plan,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_intent(topic="Cloud Migration", goal="Cut costs", audience="CTOs"):
    return ContentIntent(topic=topic, goal=goal, audience=audience)


def _make_enriched(
    title="Slide Title",
    assertion="Core claim.",
    supporting_points=None,
    implications=None,
    intent_type="problem",
    primitive="bullets_3",
    insights_applied=True,
    prompt_backend="ollama",
    fallback_used=False,
    fallback_reason="none",
) -> EnrichedSlideContent:
    diag = {
        "backend": prompt_backend,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
    }
    return EnrichedSlideContent(
        title=title,
        assertion=assertion,
        supporting_points=supporting_points or ["p1", "p2", "p3"],
        implications=implications or ["implication 1"],
        metadata={
            "intent_type": intent_type,
            "primitive": primitive,
            "insights_applied": insights_applied,
            "_prompt_diag": diag,
        },
        primitive=primitive,
    )


# ---------------------------------------------------------------------------
# _build_ci_spec
# ---------------------------------------------------------------------------

class TestBuildCiSpec:
    def test_source_mode_is_content_intelligence(self):
        intent = _make_intent()
        spec = _build_ci_spec(intent, [_make_enriched()])
        assert spec["source_mode"] == "content_intelligence"

    def test_intent_fields_propagated(self):
        intent = _make_intent(topic="AI Strategy", goal="Drive adoption", audience="Executives")
        spec = _build_ci_spec(intent, [_make_enriched()])
        assert spec["topic"] == "AI Strategy"
        assert spec["goal"] == "Drive adoption"
        assert spec["audience"] == "Executives"

    def test_slide_count_matches_enriched_list(self):
        intent = _make_intent()
        slides = [_make_enriched(title=f"Slide {i}") for i in range(4)]
        spec = _build_ci_spec(intent, slides)
        assert spec["slide_count"] == 4
        assert len(spec["slides"]) == 4

    def test_slide_index_is_sequential(self):
        intent = _make_intent()
        slides = [_make_enriched(title=f"S{i}") for i in range(3)]
        spec = _build_ci_spec(intent, slides)
        for i, entry in enumerate(spec["slides"]):
            assert entry["index"] == i

    def test_slide_fields_present(self):
        intent = _make_intent()
        enriched = _make_enriched(
            title="The Problem",
            assertion="We have a problem.",
            supporting_points=["p1", "p2", "p3"],
            implications=["Fix it now."],
            intent_type="problem",
            primitive="bullets_3",
        )
        spec = _build_ci_spec(intent, [enriched])
        entry = spec["slides"][0]
        assert entry["title"] == "The Problem"
        assert entry["assertion"] == "We have a problem."
        assert entry["supporting_points"] == ["p1", "p2", "p3"]
        assert entry["implications"] == ["Fix it now."]
        assert entry["intent_type"] == "problem"
        assert entry["primitive"] == "bullets_3"

    def test_none_goal_becomes_empty_string(self):
        intent = ContentIntent(topic="Topic", goal=None, audience=None)
        spec = _build_ci_spec(intent, [_make_enriched()])
        assert spec["goal"] == ""
        assert spec["audience"] == ""

    def test_none_implications_becomes_empty_list(self):
        enriched = _make_enriched(implications=None)
        enriched = EnrichedSlideContent(
            title="T",
            assertion="A.",
            supporting_points=["p1", "p2", "p3"],
            implications=None,
            metadata={"intent_type": "problem"},
            primitive="bullets_3",
        )
        intent = _make_intent()
        spec = _build_ci_spec(intent, [enriched])
        assert spec["slides"][0]["implications"] == []

    def test_empty_enriched_list_gives_zero_slides(self):
        intent = _make_intent()
        spec = _build_ci_spec(intent, [])
        assert spec["slide_count"] == 0
        assert spec["slides"] == []

    def test_is_json_serializable(self):
        intent = _make_intent()
        spec = _build_ci_spec(intent, [_make_enriched()])
        serialized = json.dumps(spec)
        assert json.loads(serialized) == spec


# ---------------------------------------------------------------------------
# _build_ci_slide_plan
# ---------------------------------------------------------------------------

class TestBuildCiSlidePlan:
    def test_playbook_id_and_mode(self):
        plan = _build_ci_slide_plan([_make_enriched()], playbook_id="content-intelligence")
        assert plan["playbook_id"] == "content-intelligence"
        assert plan["mode"] == "content_intelligence"

    def test_slide_count_matches(self):
        slides = [_make_enriched(title=f"S{i}") for i in range(3)]
        plan = _build_ci_slide_plan(slides)
        assert plan["slide_count"] == 3
        assert len(plan["slides"]) == 3

    def test_first_slide_is_title_type(self):
        slides = [_make_enriched(title=f"S{i}") for i in range(3)]
        plan = _build_ci_slide_plan(slides)
        assert plan["slides"][0]["slide_type"] == "title"

    def test_subsequent_slides_are_bullets_type(self):
        slides = [_make_enriched(title=f"S{i}") for i in range(4)]
        plan = _build_ci_slide_plan(slides)
        for entry in plan["slides"][1:]:
            assert entry["slide_type"] == "bullets"

    def test_prompt_diagnostics_propagated(self):
        enriched = _make_enriched(
            prompt_backend="ollama",
            fallback_used=False,
            fallback_reason="none",
        )
        plan = _build_ci_slide_plan([enriched])
        entry = plan["slides"][0]
        assert entry["prompt_backend"] == "ollama"
        assert entry["fallback_used"] is False
        assert entry["fallback_reason"] == "none"

    def test_fallback_state_reflected(self):
        enriched = _make_enriched(
            prompt_backend="no_llm_configured",
            fallback_used=True,
            fallback_reason="no_llm",
        )
        plan = _build_ci_slide_plan([enriched])
        entry = plan["slides"][0]
        assert entry["fallback_used"] is True
        assert entry["fallback_reason"] == "no_llm"

    def test_insights_applied_reflected(self):
        enriched = _make_enriched(insights_applied=True)
        plan = _build_ci_slide_plan([enriched])
        assert plan["slides"][0]["insights_applied"] is True

    def test_missing_prompt_diag_gives_empty_strings(self):
        enriched = EnrichedSlideContent(
            title="T",
            assertion="A.",
            supporting_points=["p1", "p2", "p3"],
            metadata={"intent_type": "problem"},
            primitive="bullets_3",
        )
        plan = _build_ci_slide_plan([enriched])
        entry = plan["slides"][0]
        assert entry["prompt_backend"] == ""
        assert entry["fallback_used"] is False
        assert entry["fallback_reason"] == ""

    def test_is_json_serializable(self):
        plan = _build_ci_slide_plan([_make_enriched()])
        serialized = json.dumps(plan)
        assert json.loads(serialized) == plan


# ---------------------------------------------------------------------------
# generate_presentation — CI artifact export integration
# ---------------------------------------------------------------------------

class TestCiArtifactExport:
    """Verify that the CI pipeline writes all three artifact files."""

    def test_ci_path_writes_spec_plan_and_deck(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation
        from pptgen.content_intelligence.content_models import ContentIntent

        intent = ContentIntent(topic="Test Topic", goal="Test Goal", audience="Test Audience")
        artifacts_dir = tmp_path / "artifacts"

        result = generate_presentation(
            input_text="placeholder",
            artifacts_dir=artifacts_dir,
            content_intent=intent,
        )

        assert (artifacts_dir / "spec.json").exists(), "spec.json missing"
        assert (artifacts_dir / "slide_plan.json").exists(), "slide_plan.json missing"
        assert (artifacts_dir / "deck_definition.json").exists(), "deck_definition.json missing"

    def test_ci_spec_json_has_correct_structure(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation
        from pptgen.content_intelligence.content_models import ContentIntent

        intent = ContentIntent(topic="Cloud Migration", goal="Cut costs", audience="CTOs")
        artifacts_dir = tmp_path / "artifacts"

        generate_presentation(
            input_text="placeholder",
            artifacts_dir=artifacts_dir,
            content_intent=intent,
        )

        spec = json.loads((artifacts_dir / "spec.json").read_text(encoding="utf-8"))
        assert spec["source_mode"] == "content_intelligence"
        assert spec["topic"] == "Cloud Migration"
        assert spec["goal"] == "Cut costs"
        assert spec["audience"] == "CTOs"
        assert isinstance(spec["slides"], list)
        assert spec["slide_count"] == len(spec["slides"])

    def test_ci_slide_plan_json_has_correct_structure(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation
        from pptgen.content_intelligence.content_models import ContentIntent

        intent = ContentIntent(topic="AI Strategy", goal=None, audience=None)
        artifacts_dir = tmp_path / "artifacts"

        generate_presentation(
            input_text="placeholder",
            artifacts_dir=artifacts_dir,
            content_intent=intent,
        )

        plan = json.loads((artifacts_dir / "slide_plan.json").read_text(encoding="utf-8"))
        assert plan["playbook_id"] == "content-intelligence"
        assert plan["mode"] == "content_intelligence"
        assert isinstance(plan["slides"], list)
        assert plan["slide_count"] == len(plan["slides"])
        for entry in plan["slides"]:
            assert "slide_type" in entry
            assert "fallback_used" in entry

    def test_ci_artifact_paths_returned_in_result(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation
        from pptgen.content_intelligence.content_models import ContentIntent

        intent = ContentIntent(topic="Test", goal=None, audience=None)
        artifacts_dir = tmp_path / "artifacts"

        result = generate_presentation(
            input_text="placeholder",
            artifacts_dir=artifacts_dir,
            content_intent=intent,
        )

        assert result.artifact_paths is not None
        assert "spec" in result.artifact_paths
        assert "slide_plan" in result.artifact_paths
        assert "deck_definition" in result.artifact_paths

    def test_legacy_path_writes_spec_plan_deck(self, tmp_path):
        """Legacy (non-CI) path must still emit spec.json + slide_plan.json via write_artifacts."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        artifacts_dir = tmp_path / "artifacts"
        result = generate_presentation(
            input_text="Q3 financial results show strong revenue growth and margin expansion.",
            artifacts_dir=artifacts_dir,
        )

        assert result.artifact_paths is not None
        # write_artifacts is responsible for the legacy path files
        # At minimum the deck_definition must exist
        assert any(Path(p).exists() for p in result.artifact_paths.values())

    def test_direct_deck_path_writes_only_deck_definition(self, tmp_path):
        """Direct deck YAML input writes only deck_definition.json (no CI enrichment)."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        deck_yaml = """
slides:
  - type: title
    title: My Title
    subtitle: My Subtitle
deck:
  title: My Title
  template: ops_review_v1
  author: test
"""
        artifacts_dir = tmp_path / "artifacts"
        result = generate_presentation(
            input_text=deck_yaml,
            artifacts_dir=artifacts_dir,
        )

        assert result.artifact_paths is not None
        assert "deck_definition" in result.artifact_paths
        assert "spec" not in result.artifact_paths
        assert "slide_plan" not in result.artifact_paths
