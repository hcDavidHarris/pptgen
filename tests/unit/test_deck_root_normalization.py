"""Regression tests for Phase 9 deck root shape normalization.

The bug: Phase 9 structured deck input uses top-level title/theme/slides
(no 'deck:' wrapper).  DeckFile.model_validate() required a 'deck:' block
and rejected 'title' as an extra top-level key with:
  - deck: Field required
  - title: Extra inputs are not permitted

Fix: _normalize_deck_root_shape() in yaml_loader.py detects the Phase 9 root
shape (slides present, deck absent) and promotes metadata fields into a
'deck' block before validation.  Legacy input passes through unchanged.

Covers:
- _normalize_deck_root_shape leaves legacy deck+slides unchanged
- _normalize_deck_root_shape leaves data without slides unchanged
- _normalize_deck_root_shape builds deck block from top-level fields
- title, template, author defaults applied when absent
- theme, primitive, content, layout, slots remain at top level
- tags list preserved when present
- parse_deck() accepts legacy shape unchanged
- parse_deck() accepts Phase 9 root shape with top-level title/theme
- parse_deck() applies title/template/author defaults for minimal input
- parse_deck() still rejects genuinely malformed input
- primitive slides in Phase 9 root shape parse correctly after normalization
- generate_presentation() resolves template from top-level template field
- generate_presentation() with Phase 9 root shape bypasses extraction
- generate_presentation() reaches deck_planned without validation errors
- original failing shape (title/theme/slides at top level) now succeeds
"""
from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from pptgen.errors import ParseError
from pptgen.loaders.yaml_loader import _normalize_deck_root_shape, parse_deck
from pptgen.models.deck import DeckFile
from pptgen.models.slides import PrimitiveSlide, TitleSlide
from pptgen.pipeline.generation_pipeline import generate_presentation


# ---------------------------------------------------------------------------
# TestNormalizeDeckRootShape — unit tests for the normalization helper
# ---------------------------------------------------------------------------


class TestNormalizeDeckRootShape:
    def test_legacy_shape_unchanged(self):
        data = {
            "deck": {"title": "T", "template": "tmpl", "author": "A"},
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        result = _normalize_deck_root_shape(data)
        assert result is data  # exact same object — not copied

    def test_no_slides_key_unchanged(self):
        data = {"title": "T", "template": "tmpl"}
        result = _normalize_deck_root_shape(data)
        assert result is data

    def test_phase9_root_builds_deck_block(self):
        data = {
            "title": "Interchange DevOps",
            "theme": "executive",
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        result = _normalize_deck_root_shape(data)
        assert "deck" in result
        assert result["deck"]["title"] == "Interchange DevOps"

    def test_title_moved_into_deck(self):
        data = {"title": "My Title", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["title"] == "My Title"
        assert "title" not in result

    def test_template_moved_into_deck(self):
        data = {"title": "T", "template": "ops_review_v1", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["template"] == "ops_review_v1"
        assert "template" not in result

    def test_author_moved_into_deck(self):
        data = {"title": "T", "author": "Alice", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["author"] == "Alice"
        assert "author" not in result

    def test_subtitle_moved_into_deck(self):
        data = {"title": "T", "subtitle": "Sub", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["subtitle"] == "Sub"
        assert "subtitle" not in result

    def test_version_moved_into_deck(self):
        data = {"title": "T", "version": "2.0", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["version"] == "2.0"
        assert "version" not in result

    def test_tags_moved_into_deck(self):
        data = {"title": "T", "tags": ["ops", "q3"], "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["tags"] == ["ops", "q3"]
        assert "tags" not in result

    def test_default_title_applied_when_absent(self):
        data = {"slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["title"] == "Untitled Deck"

    def test_default_template_applied_when_absent(self):
        data = {"title": "T", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["template"] == "ops_review_v1"

    def test_default_author_applied_when_absent(self):
        data = {"title": "T", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["deck"]["author"] == "Unknown"

    def test_theme_stays_at_top_level(self):
        data = {"title": "T", "theme": "executive", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["theme"] == "executive"
        assert "theme" not in result.get("deck", {})

    def test_primitive_stays_at_top_level(self):
        data = {"title": "T", "primitive": "bullet_slide", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["primitive"] == "bullet_slide"
        assert "primitive" not in result.get("deck", {})

    def test_content_stays_at_top_level(self):
        data = {"title": "T", "content": {"title": "Q3"}, "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["content"]["title"] == "Q3"

    def test_slides_preserved_at_top_level(self):
        slides = [{"type": "title", "title": "T", "subtitle": "S"}]
        data = {"title": "T", "slides": slides}
        result = _normalize_deck_root_shape(data)
        assert result["slides"] is slides

    def test_empty_slides_preserved(self):
        data = {"title": "T", "slides": []}
        result = _normalize_deck_root_shape(data)
        assert result["slides"] == []


# ---------------------------------------------------------------------------
# TestParseDeckNormalization — parse_deck() accepts both shapes
# ---------------------------------------------------------------------------


class TestParseDeckNormalization:
    def test_legacy_shape_still_parses(self):
        data = {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        deck = parse_deck(data)
        assert isinstance(deck, DeckFile)
        assert deck.deck.title == "T"

    def test_phase9_root_shape_parses(self):
        data = {
            "title": "Interchange DevOps Transformation",
            "theme": "executive",
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        deck = parse_deck(data)
        assert isinstance(deck, DeckFile)
        assert deck.deck.title == "Interchange DevOps Transformation"

    def test_theme_preserved_in_phase9_root_parse(self):
        data = {
            "title": "T",
            "theme": "executive",
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        deck = parse_deck(data)
        assert deck.theme == "executive"

    def test_template_from_top_level_goes_into_deck(self):
        data = {
            "title": "T",
            "template": "architecture_overview_v1",
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        deck = parse_deck(data)
        assert deck.deck.template == "architecture_overview_v1"

    def test_author_default_applied_on_minimal_input(self):
        data = {
            "title": "T",
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        deck = parse_deck(data)
        assert deck.deck.author == "Unknown"

    def test_title_default_applied_when_absent(self):
        data = {
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        deck = parse_deck(data)
        assert deck.deck.title == "Untitled Deck"

    def test_primitive_slide_in_phase9_root_shape_parses(self):
        data = {
            "title": "Platform Deck",
            "theme": "executive",
            "slides": [
                {"primitive": "bullet_slide", "content": {"title": "Q3", "bullets": ["a"]}},
            ],
        }
        deck = parse_deck(data)
        assert isinstance(deck.slides[0], PrimitiveSlide)
        assert deck.slides[0].primitive == "bullet_slide"

    def test_top_level_primitive_in_phase9_root_shape_parses(self):
        data = {
            "title": "Platform",
            "primitive": "title_slide",
            "content": {"title": "Platform", "subtitle": "Overview"},
            "slides": [{"type": "title", "title": "Platform", "subtitle": "Overview"}],
        }
        deck = parse_deck(data)
        assert deck.primitive == "title_slide"

    def test_malformed_input_still_raises(self):
        """Non-normalizable input still raises ParseError."""
        with pytest.raises(ParseError):
            parse_deck({"slides": "not-a-list"})

    def test_missing_slides_still_raises(self):
        with pytest.raises(ParseError):
            parse_deck({"deck": {"title": "T", "template": "t", "author": "a"}})

    def test_unknown_extra_top_level_key_still_raises(self):
        """extra='forbid' still rejects genuinely unknown keys."""
        with pytest.raises(ParseError):
            parse_deck({
                "deck": {"title": "T", "template": "t", "author": "a"},
                "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
                "completely_unknown_key": "bad",
            })


# ---------------------------------------------------------------------------
# TestGeneratePresentationRootShape — integration: Phase 9 root format through
# the full pipeline without extraction errors
# ---------------------------------------------------------------------------


class TestGeneratePresentationRootShape:
    # The exact failing pattern from the problem statement.
    FAILING_YAML = textwrap.dedent("""\
        title: "Interchange DevOps Transformation"
        theme: executive
        slides:
          - primitive: title_slide
            content:
              title: "Interchange DevOps Platform"
              subtitle: "From Fragmented Operations to Scalable System"
          - primitive: bullet_slide
            content:
              title: "Architecture Overview"
              bullets:
                - "CI/CD pipeline automation"
                - "Infrastructure as Code"
                - "Observability stack"
    """)

    def test_phase9_root_shape_bypasses_extraction(self):
        result = generate_presentation(self.FAILING_YAML)
        assert result.playbook_id == "direct-deck-input"

    def test_phase9_root_shape_reaches_deck_planned(self):
        result = generate_presentation(self.FAILING_YAML)
        assert result.stage == "deck_planned"

    def test_no_raw_yaml_lines_as_bullet_text(self):
        result = generate_presentation(self.FAILING_YAML)
        for slide in result.deck_definition.get("slides", []):
            for bullet in slide.get("bullets", []):
                assert "primitive:" not in bullet
                assert "theme:" not in bullet

    def test_primitive_slides_preserved_in_deck_definition(self):
        result = generate_presentation(self.FAILING_YAML)
        slides = result.deck_definition.get("slides", [])
        assert slides[0].get("primitive") == "title_slide"
        assert slides[1].get("primitive") == "bullet_slide"

    def test_theme_preserved_in_deck_definition(self):
        result = generate_presentation(self.FAILING_YAML)
        assert result.deck_definition.get("theme") == "executive"

    def test_template_resolved_from_top_level_template_field(self):
        yaml_with_template = textwrap.dedent("""\
            title: "DevOps Platform"
            template: "architecture_overview_v1"
            slides:
              - type: title
                id: slide-1
                title: "DevOps Platform"
                subtitle: "Overview"
                notes: null
                visible: true
        """)
        result = generate_presentation(yaml_with_template)
        assert result.template_id == "architecture_overview_v1"

    def test_template_falls_back_to_default_when_absent(self):
        yaml_no_template = textwrap.dedent("""\
            title: "Minimal Deck"
            slides:
              - type: title
                id: slide-1
                title: "Minimal"
                subtitle: "Deck"
                notes: null
                visible: true
        """)
        result = generate_presentation(yaml_no_template)
        assert result.template_id == "ops_review_v1"

    def test_mixed_primitive_and_legacy_slides_in_root_shape(self):
        yaml_mixed = textwrap.dedent("""\
            title: "Mixed Deck"
            theme: executive
            slides:
              - type: title
                id: slide-1
                title: "Mixed Deck"
                subtitle: "Overview"
                notes: null
                visible: true
              - primitive: bullet_slide
                content:
                  title: "Key Points"
                  bullets:
                    - "Point one"
                    - "Point two"
        """)
        result = generate_presentation(yaml_mixed)
        assert result.playbook_id == "direct-deck-input"
        slides = result.deck_definition["slides"]
        assert slides[0]["type"] == "title"
        assert slides[1]["primitive"] == "bullet_slide"

    def test_no_deck_field_required_error(self):
        """Core regression: 'deck: Field required' must not occur."""
        # If this raises, it will be a PipelineError mentioning 'deck'.
        # If it doesn't raise, the test passes.
        result = generate_presentation(self.FAILING_YAML)
        assert result is not None

    def test_no_title_extra_inputs_error(self):
        """Core regression: 'title: Extra inputs are not permitted' must not occur."""
        result = generate_presentation(self.FAILING_YAML)
        assert result is not None

    def test_legacy_deck_shape_still_works(self):
        yaml_legacy = textwrap.dedent("""\
            deck:
              title: "Legacy Deck"
              template: "ops_review_v1"
              author: "Team"
              version: "1.0"
            slides:
              - type: title
                id: slide-1
                title: "Legacy Deck"
                subtitle: "Overview"
                notes: null
                visible: true
        """)
        result = generate_presentation(yaml_legacy)
        assert result.playbook_id == "direct-deck-input"
        assert result.deck_definition["deck"]["title"] == "Legacy Deck"
