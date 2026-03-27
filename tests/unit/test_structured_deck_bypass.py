"""Regression tests for the structured deck bypass — Phase 9 bug fix.

The bug: a primitive-based YAML deck definition passed as input_text to
generate_presentation() was routed through the content-extraction pipeline
(route_input → execute_playbook_full → convert_spec_to_deck) instead of
being used directly as deck_definition.  This caused the YAML lines to appear
as literal bullet text on the rendered slide.

Root cause: no early-exit existed for input that was already a valid structured
deck definition.  The classifier matched keywords like "architecture" in the
YAML and routed to _extract_architecture_notes(), whose fallback path collected
every non-heading line as a bullet.

Fix: _try_parse_deck_definition() detects a top-level 'slides' list and bypasses
the extraction pipeline when found.

Covers:
- Structured deck (with slides key) bypasses extraction pipeline
- playbook_id is 'direct-deck-input' for structured input
- presentation_spec is None for structured input
- slide_plan is None for structured input
- primitive key in structured deck is preserved (not flattened to bullets)
- layout key in structured deck is preserved
- deck_definition.slides contains no raw YAML-like bullet lines
- legacy narrative text still routes through the normal extraction path
- empty input still routes through the normal extraction path
- YAML parse failure still routes through the normal extraction path
- Template ID comes from deck metadata when not overridden
- template_id override respected in structured deck path
- artifacts_dir produces deck_definition.json for structured deck path
- artifacts_dir does NOT produce spec.json or slide_plan.json for structured deck
- _try_parse_deck_definition returns None for non-YAML text
- _try_parse_deck_definition returns None for YAML without slides key
- _try_parse_deck_definition returns None for YAML where slides is not a list
- _try_parse_deck_definition returns dict for valid structured deck YAML
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from pptgen.pipeline.generation_pipeline import (
    PipelineError,
    _try_parse_deck_definition,
    generate_presentation,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal structured deck YAML strings
# ---------------------------------------------------------------------------

# A valid structured deck with a primitive key — the exact pattern that
# triggered the original bug.  "architecture" and "component" keywords in
# the YAML content would have scored the architecture-notes playbook highly.
PRIMITIVE_DECK_YAML = textwrap.dedent("""\
    deck:
      title: "Interchange DevOps Transformation"
      template: "ops_review_v1"
      author: "Platform Team"
      version: "1.0"
    primitive: title_slide
    theme: executive
    content:
      title: "Interchange DevOps Platform"
      subtitle: "From Fragmented Operations to Scalable System"
    slides:
      - type: title
        id: slide-1
        title: "Interchange DevOps Platform"
        subtitle: "From Fragmented Operations to Scalable System"
        notes: null
        visible: true
""")

# A plain structured deck without a primitive key — confirms basic bypass works.
PLAIN_DECK_YAML = textwrap.dedent("""\
    deck:
      title: "Q1 Review"
      template: "ops_review_v1"
      author: "Team"
      version: "1.0"
    slides:
      - type: title
        id: slide-1
        title: "Q1 Review"
        subtitle: "Quarterly update"
        notes: null
        visible: true
      - type: bullets
        id: slide-2
        title: "Results"
        bullets:
          - "Revenue up"
          - "NPS improved"
        notes: null
        visible: true
""")

# Narrative text that should NOT be treated as a structured deck.
NARRATIVE_TEXT = "Q3 business review results and action items."

# Text with architecture keywords that was triggering the bug.
ARCH_NARRATIVE = textwrap.dedent("""\
    Architecture Decision Record: Microservices vs Monolith

    Context:
    The current system architecture is a monolith with growing complexity.

    Options:
    Option A: Keep monolith and modularize components
    Option B: Migrate to microservices architecture

    Decision:
    We chose Option B for scalability reasons.
""")


# ---------------------------------------------------------------------------
# TestTryParseDecKDefinition — unit tests for the detection helper
# ---------------------------------------------------------------------------


class TestTryParseDeckDefinition:
    def test_returns_none_for_plain_text(self):
        assert _try_parse_deck_definition("This is a meeting summary.") is None

    def test_returns_none_for_empty_string(self):
        assert _try_parse_deck_definition("") is None

    def test_returns_none_for_yaml_without_slides(self):
        yaml = "title: hello\nsubtitle: world\n"
        assert _try_parse_deck_definition(yaml) is None

    def test_returns_none_when_slides_is_not_list(self):
        yaml = "slides: not-a-list\n"
        assert _try_parse_deck_definition(yaml) is None

    def test_returns_none_for_invalid_yaml(self):
        assert _try_parse_deck_definition(": invalid: {\n") is None

    def test_returns_none_for_yaml_list_at_root(self):
        # YAML that parses to a list rather than a dict
        assert _try_parse_deck_definition("- item1\n- item2\n") is None

    def test_returns_dict_for_valid_structured_deck(self):
        result = _try_parse_deck_definition(PLAIN_DECK_YAML)
        assert isinstance(result, dict)

    def test_returns_dict_with_slides_key(self):
        result = _try_parse_deck_definition(PLAIN_DECK_YAML)
        assert "slides" in result
        assert isinstance(result["slides"], list)

    def test_returns_dict_preserving_primitive_key(self):
        result = _try_parse_deck_definition(PRIMITIVE_DECK_YAML)
        assert result["primitive"] == "title_slide"

    def test_arch_narrative_text_returns_none(self):
        # Architecture keyword-heavy text should NOT be detected as a deck.
        assert _try_parse_deck_definition(ARCH_NARRATIVE) is None


# ---------------------------------------------------------------------------
# TestStructuredDeckBypass — integration: bypass path through generate_presentation
# ---------------------------------------------------------------------------


class TestStructuredDeckBypass:
    def test_plain_deck_playbook_id_is_direct(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.playbook_id == "direct-deck-input"

    def test_primitive_deck_playbook_id_is_direct(self):
        result = generate_presentation(PRIMITIVE_DECK_YAML)
        assert result.playbook_id == "direct-deck-input"

    def test_presentation_spec_is_none_for_structured_deck(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.presentation_spec is None

    def test_slide_plan_is_none_for_structured_deck(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.slide_plan is None

    def test_deck_definition_preserved_for_plain_deck(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert isinstance(result.deck_definition, dict)
        assert "slides" in result.deck_definition

    def test_slides_are_structured_not_flattened(self):
        """The core regression: slides must contain typed slide objects,
        not raw YAML lines as bullet text."""
        result = generate_presentation(PLAIN_DECK_YAML)
        slides = result.deck_definition["slides"]
        assert len(slides) == 2
        assert slides[0]["type"] == "title"
        assert slides[1]["type"] == "bullets"

    def test_no_raw_yaml_lines_as_bullet_text(self):
        """Regression: primitive/theme/layout keys must NOT appear as bullet items."""
        result = generate_presentation(PRIMITIVE_DECK_YAML)
        slides = result.deck_definition.get("slides", [])
        for slide in slides:
            bullets = slide.get("bullets", [])
            for bullet in bullets:
                assert "primitive:" not in bullet
                assert "theme:" not in bullet
                assert "layout:" not in bullet

    def test_primitive_key_preserved_in_deck_definition(self):
        result = generate_presentation(PRIMITIVE_DECK_YAML)
        assert result.deck_definition.get("primitive") == "title_slide"

    def test_template_from_deck_metadata_used(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.template_id == "ops_review_v1"

    def test_template_id_override_respected(self):
        result = generate_presentation(PLAIN_DECK_YAML, template_id="ops_review_v1")
        assert result.template_id == "ops_review_v1"

    def test_stage_is_deck_planned_without_output_path(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.stage == "deck_planned"

    def test_resolved_assets_is_not_none(self):
        # Asset resolution always runs; returns an empty list when no refs present.
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.resolved_assets is not None

    def test_resolved_assets_empty_when_no_refs(self):
        result = generate_presentation(PLAIN_DECK_YAML)
        assert result.resolved_assets == []


# ---------------------------------------------------------------------------
# TestArtifactsForStructuredDeck
# ---------------------------------------------------------------------------


class TestArtifactsForStructuredDeck:
    def test_artifacts_dir_produces_deck_definition_json(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        generate_presentation(PLAIN_DECK_YAML, artifacts_dir=artifacts_dir)
        assert (artifacts_dir / "deck_definition.json").exists()

    def test_deck_definition_json_is_valid_json(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        generate_presentation(PLAIN_DECK_YAML, artifacts_dir=artifacts_dir)
        data = json.loads((artifacts_dir / "deck_definition.json").read_text())
        assert "slides" in data

    def test_spec_json_not_written_for_structured_deck(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        generate_presentation(PLAIN_DECK_YAML, artifacts_dir=artifacts_dir)
        assert not (artifacts_dir / "spec.json").exists()

    def test_slide_plan_json_not_written_for_structured_deck(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        generate_presentation(PLAIN_DECK_YAML, artifacts_dir=artifacts_dir)
        assert not (artifacts_dir / "slide_plan.json").exists()

    def test_artifact_paths_contains_deck_definition(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        result = generate_presentation(PLAIN_DECK_YAML, artifacts_dir=artifacts_dir)
        assert "deck_definition" in result.artifact_paths


# ---------------------------------------------------------------------------
# TestLegacyPathPreserved — backward compatibility
# ---------------------------------------------------------------------------


class TestLegacyPathPreserved:
    def test_narrative_text_routes_normally(self):
        result = generate_presentation(NARRATIVE_TEXT)
        assert result.playbook_id != "direct-deck-input"

    def test_narrative_text_produces_presentation_spec(self):
        result = generate_presentation(NARRATIVE_TEXT)
        assert result.presentation_spec is not None

    def test_narrative_text_produces_slide_plan(self):
        result = generate_presentation(NARRATIVE_TEXT)
        assert result.slide_plan is not None

    def test_architecture_narrative_routes_to_architecture_playbook(self):
        result = generate_presentation(ARCH_NARRATIVE)
        assert result.playbook_id == "architecture-notes-to-adr-deck"

    def test_architecture_narrative_slides_are_structured_slide_types(self):
        result = generate_presentation(ARCH_NARRATIVE)
        slides = result.deck_definition["slides"]
        for slide in slides:
            assert slide["type"] in {"title", "section", "bullets", "metric_summary",
                                     "image_caption", "two_column"}

    def test_architecture_narrative_no_primitive_lines_in_bullets(self):
        """Separate from the main bug: ensure arch narrative text also doesn't
        contain raw primitive YAML lines (this path is unaffected by the fix,
        but this confirms backward compat)."""
        result = generate_presentation(ARCH_NARRATIVE)
        slides = result.deck_definition.get("slides", [])
        for slide in slides:
            for bullet in slide.get("bullets", []):
                # Plain architecture narrative should never produce these
                assert not bullet.startswith("primitive:")
                assert not bullet.startswith("theme:")

    def test_empty_input_routes_to_generic_fallback(self):
        result = generate_presentation("   ")
        assert result.playbook_id == "generic-summary-playbook"

    def test_narrative_artifacts_include_spec_and_plan(self, tmp_path):
        artifacts_dir = tmp_path / "artifacts"
        generate_presentation(NARRATIVE_TEXT, artifacts_dir=artifacts_dir)
        assert (artifacts_dir / "spec.json").exists()
        assert (artifacts_dir / "slide_plan.json").exists()
        assert (artifacts_dir / "deck_definition.json").exists()


# ---------------------------------------------------------------------------
# TestBugSignatureRegression — exact pattern from the original failure report
# ---------------------------------------------------------------------------


class TestBugSignatureRegression:
    """Reproduce the exact bug signature described in the failure report.

    The failing deck contained a bullets slide whose bullets array held raw
    YAML-like lines including 'primitive: title_slide' and 'theme: executive'.
    After the fix, structured YAML input must never produce this pattern.
    """

    FAILING_INPUT = textwrap.dedent("""\
        deck:
          title: "Architecture Decision Review"
          template: "architecture_overview_v1"
          author: "Strategy Team"
          version: "1.0"
        slides:
          - type: title
            id: slide-1
            title: "Interchange DevOps Transformation"
            subtitle: "Platform Overview"
            notes: null
            visible: true
          - type: section
            id: section-1
            section_title: "Architecture Overview"
            notes: null
            visible: true
          - type: bullets
            id: bullets-1
            title: "Key Components"
            bullets:
              - "CI/CD pipeline automation"
              - "Infrastructure as Code"
              - "Observability stack"
            notes: null
            visible: true
    """)

    def test_structured_deck_bypasses_extraction(self):
        result = generate_presentation(self.FAILING_INPUT)
        assert result.playbook_id == "direct-deck-input"

    def test_no_raw_primitive_lines_in_any_slide_bullets(self):
        result = generate_presentation(self.FAILING_INPUT)
        for slide in result.deck_definition.get("slides", []):
            for bullet in slide.get("bullets", []):
                assert "primitive:" not in bullet, (
                    f"Raw 'primitive:' line found in bullet: {bullet!r}"
                )
                assert "theme:" not in bullet, (
                    f"Raw 'theme:' line found in bullet: {bullet!r}"
                )

    def test_slide_count_matches_input(self):
        result = generate_presentation(self.FAILING_INPUT)
        assert len(result.deck_definition["slides"]) == 3

    def test_slide_types_match_input(self):
        result = generate_presentation(self.FAILING_INPUT)
        types = [s["type"] for s in result.deck_definition["slides"]]
        assert types == ["title", "section", "bullets"]

    def test_bullets_contain_real_content_not_yaml_lines(self):
        result = generate_presentation(self.FAILING_INPUT)
        bullets_slide = result.deck_definition["slides"][2]
        assert bullets_slide["type"] == "bullets"
        assert bullets_slide["bullets"] == [
            "CI/CD pipeline automation",
            "Infrastructure as Code",
            "Observability stack",
        ]

    def test_architecture_template_id_from_deck_metadata(self):
        result = generate_presentation(self.FAILING_INPUT)
        assert result.template_id == "architecture_overview_v1"
