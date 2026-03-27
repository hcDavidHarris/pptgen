"""Regression tests for Phase 9 primitive slide schema support.

The bug: DeckFile rejected extra top-level keys (primitive, theme, content,
layout, slots) with 'Extra inputs are not permitted', and slides with a
'primitive' key instead of 'type' failed the discriminated union with
'Unable to extract tag using discriminator'.

Fix: PrimitiveSlide added to SlideUnion via callable Discriminator; Phase 9
fields added as explicit optional fields on DeckFile.

Covers:
- Legacy slides still validate (all six types)
- PrimitiveSlide validates (primitive + content)
- Mixed legacy + primitive slides in same deck
- Unknown type value still raises (discriminator returns unknown tag)
- Unknown top-level key still raises (extra='forbid' preserved)
- Phase 9 top-level keys accepted: primitive, theme, content, layout, slots
- PrimitiveSlide.extra='ignore' allows injected Phase 9 keys
- PrimitiveSlide fields: primitive, content, id, notes, visible
- PrimitiveSlide.content defaults to empty dict
- DeckFile with slide-level primitive slides validates end-to-end
- parse_deck() accepts primitive deck format
- generate_presentation() with primitive slides in deck reaches Phase 9 stages
"""
from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from pptgen.loaders.yaml_loader import parse_deck
from pptgen.models.deck import DeckFile
from pptgen.models.slides import (
    BulletsSlide,
    ImageCaptionSlide,
    MetricItem,
    MetricSummarySlide,
    PrimitiveSlide,
    SectionSlide,
    SlideUnion,
    TitleSlide,
    TwoColumnSlide,
)
from pptgen.pipeline.generation_pipeline import generate_presentation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_deck(slide_data: dict) -> dict:
    """Build a minimal valid DeckFile dict with one slide."""
    return {
        "deck": {"title": "Test", "template": "ops_review_v1", "author": "Tester"},
        "slides": [slide_data],
    }


def _parse_slide(data: dict):
    """Parse a single slide via the SlideUnion type annotation."""
    deck = _minimal_deck(data)
    return DeckFile.model_validate(deck).slides[0]


# ---------------------------------------------------------------------------
# TestLegacySlidesUnchanged — all existing slide types still validate
# ---------------------------------------------------------------------------


class TestLegacySlidesUnchanged:
    def test_title_slide_validates(self):
        s = _parse_slide({"type": "title", "title": "T", "subtitle": "S"})
        assert isinstance(s, TitleSlide)

    def test_section_slide_validates(self):
        s = _parse_slide({"type": "section", "section_title": "Section"})
        assert isinstance(s, SectionSlide)

    def test_bullets_slide_validates(self):
        s = _parse_slide({"type": "bullets", "title": "T", "bullets": ["a", "b"]})
        assert isinstance(s, BulletsSlide)

    def test_two_column_slide_validates(self):
        s = _parse_slide({
            "type": "two_column",
            "title": "T",
            "left_content": ["L"],
            "right_content": ["R"],
        })
        assert isinstance(s, TwoColumnSlide)

    def test_metric_summary_slide_validates(self):
        s = _parse_slide({
            "type": "metric_summary",
            "title": "T",
            "metrics": [{"label": "Revenue", "value": "99%"}],
        })
        assert isinstance(s, MetricSummarySlide)

    def test_image_caption_slide_validates(self):
        s = _parse_slide({
            "type": "image_caption",
            "title": "T",
            "image_path": "img.png",
            "caption": "Caption",
        })
        assert isinstance(s, ImageCaptionSlide)

    def test_unknown_type_still_raises(self):
        with pytest.raises(ValidationError):
            _parse_slide({"type": "chart", "title": "T"})

    def test_unknown_slide_field_still_raises(self):
        with pytest.raises(ValidationError):
            _parse_slide({"type": "title", "title": "T", "subtitle": "S", "extra": "bad"})


# ---------------------------------------------------------------------------
# TestPrimitiveSlideModel — unit tests for PrimitiveSlide itself
# ---------------------------------------------------------------------------


class TestPrimitiveSlideModel:
    def test_parses_primitive_and_content(self):
        s = _parse_slide({
            "primitive": "bullet_slide",
            "content": {"title": "Q3 Results", "bullets": ["Revenue up"]},
        })
        assert isinstance(s, PrimitiveSlide)
        assert s.primitive == "bullet_slide"
        assert s.content["title"] == "Q3 Results"

    def test_content_defaults_to_empty_dict(self):
        s = _parse_slide({"primitive": "title_slide"})
        assert isinstance(s, PrimitiveSlide)
        assert s.content == {}

    def test_id_optional(self):
        s = _parse_slide({"primitive": "title_slide", "id": "slide-1"})
        assert s.id == "slide-1"

    def test_notes_optional(self):
        s = _parse_slide({"primitive": "title_slide", "notes": "Speaker notes"})
        assert s.notes == "Speaker notes"

    def test_visible_defaults_to_true(self):
        s = _parse_slide({"primitive": "title_slide"})
        assert s.visible is True

    def test_visible_can_be_false(self):
        s = _parse_slide({"primitive": "title_slide", "visible": False})
        assert s.visible is False

    def test_primitive_field_required(self):
        with pytest.raises(ValidationError):
            _parse_slide({"content": {"title": "T"}})  # no primitive key, no type key

    def test_primitive_field_must_be_nonempty(self):
        with pytest.raises(ValidationError):
            PrimitiveSlide.model_validate({"primitive": ""})

    def test_extra_fields_ignored_not_rejected(self):
        # Phase 9 resolution stages inject 'layout' and 'slots'; these must
        # not cause a ValidationError.
        s = PrimitiveSlide.model_validate({
            "primitive": "bullet_slide",
            "content": {},
            "layout": "single_column",
            "slots": {"content": {"title": "T"}},
        })
        assert s.primitive == "bullet_slide"

    def test_all_six_known_primitives_accepted(self):
        for pid in [
            "title_slide", "section_slide", "bullet_slide",
            "comparison_slide", "metrics_slide", "image_text_slide",
        ]:
            s = _parse_slide({"primitive": pid, "content": {}})
            assert isinstance(s, PrimitiveSlide)
            assert s.primitive == pid


# ---------------------------------------------------------------------------
# TestMixedDeck — legacy and primitive slides in the same DeckFile
# ---------------------------------------------------------------------------


class TestMixedDeck:
    def test_mixed_slides_validate(self):
        data = {
            "deck": {"title": "Mixed", "template": "ops_review_v1", "author": "T"},
            "slides": [
                {"type": "title", "title": "T", "subtitle": "S"},
                {"primitive": "bullet_slide", "content": {"title": "Q3", "bullets": ["a"]}},
                {"type": "bullets", "title": "Results", "bullets": ["b"]},
            ],
        }
        deck = DeckFile.model_validate(data)
        assert len(deck.slides) == 3
        assert isinstance(deck.slides[0], TitleSlide)
        assert isinstance(deck.slides[1], PrimitiveSlide)
        assert isinstance(deck.slides[2], BulletsSlide)


# ---------------------------------------------------------------------------
# TestDeckFilePhase9Fields — top-level Phase 9 keys are now accepted
# ---------------------------------------------------------------------------


class TestDeckFilePhase9Fields:
    def _base_deck(self) -> dict:
        return {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }

    def test_primitive_top_level_accepted(self):
        data = {**self._base_deck(), "primitive": "bullet_slide"}
        deck = DeckFile.model_validate(data)
        assert deck.primitive == "bullet_slide"

    def test_theme_top_level_accepted(self):
        data = {**self._base_deck(), "theme": "executive"}
        deck = DeckFile.model_validate(data)
        assert deck.theme == "executive"

    def test_content_top_level_accepted(self):
        data = {**self._base_deck(), "content": {"title": "Q3", "bullets": ["a"]}}
        deck = DeckFile.model_validate(data)
        assert deck.content["title"] == "Q3"

    def test_layout_top_level_accepted(self):
        data = {**self._base_deck(), "layout": "single_column"}
        deck = DeckFile.model_validate(data)
        assert deck.layout == "single_column"

    def test_slots_top_level_accepted(self):
        data = {**self._base_deck(), "slots": {"content": {"title": "T"}}}
        deck = DeckFile.model_validate(data)
        assert deck.slots["content"]["title"] == "T"

    def test_all_phase9_fields_together(self):
        data = {
            **self._base_deck(),
            "primitive": "bullet_slide",
            "theme": "executive",
            "content": {"title": "Q3"},
            "layout": "single_column",
            "slots": {"content": {"title": "Q3"}},
        }
        deck = DeckFile.model_validate(data)
        assert deck.primitive == "bullet_slide"
        assert deck.theme == "executive"

    def test_phase9_fields_default_to_none(self):
        deck = DeckFile.model_validate(self._base_deck())
        assert deck.primitive is None
        assert deck.theme is None
        assert deck.content is None
        assert deck.layout is None
        assert deck.slots is None

    def test_unknown_extra_key_still_raises(self):
        """extra='forbid' must still reject genuinely unknown top-level keys."""
        data = {**self._base_deck(), "extra_key": "not allowed"}
        with pytest.raises(ValidationError, match="Extra inputs"):
            DeckFile.model_validate(data)


# ---------------------------------------------------------------------------
# TestParseDeck — parse_deck() accepts structured primitive decks
# ---------------------------------------------------------------------------


class TestParseDeck:
    def test_legacy_deck_still_parses(self):
        data = {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "slides": [{"type": "title", "title": "Title", "subtitle": "Sub"}],
        }
        deck = parse_deck(data)
        assert isinstance(deck, DeckFile)
        assert isinstance(deck.slides[0], TitleSlide)

    def test_primitive_slide_deck_parses(self):
        data = {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "slides": [
                {"primitive": "bullet_slide", "content": {"title": "Q3", "bullets": ["a"]}},
            ],
        }
        deck = parse_deck(data)
        assert isinstance(deck.slides[0], PrimitiveSlide)

    def test_deck_with_top_level_primitive_parses(self):
        data = {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "primitive": "title_slide",
            "theme": "executive",
            "content": {"title": "Platform", "subtitle": "Overview"},
            "slides": [{"type": "title", "title": "Platform", "subtitle": "Overview"}],
        }
        deck = parse_deck(data)
        assert deck.primitive == "title_slide"
        assert deck.theme == "executive"


# ---------------------------------------------------------------------------
# TestGeneratePresentationPrimitiveSlides — integration: primitive slides in
# slides[] array reach Phase 9 stages without being flattened
# ---------------------------------------------------------------------------


class TestGeneratePresentationPrimitiveSlides:
    PRIMITIVE_SLIDES_YAML = textwrap.dedent("""\
        deck:
          title: "Interchange DevOps Platform"
          template: "ops_review_v1"
          author: "Platform Team"
          version: "1.0"
        slides:
          - type: title
            id: slide-1
            title: "Interchange DevOps Platform"
            subtitle: "Platform Overview"
            notes: null
            visible: true
          - primitive: bullet_slide
            id: slide-2
            content:
              title: "Key Results"
              bullets:
                - "CI/CD fully automated"
                - "Deployment frequency 10x"
            notes: null
            visible: true
    """)

    def test_primitive_slides_yaml_bypasses_extraction(self):
        result = generate_presentation(self.PRIMITIVE_SLIDES_YAML)
        assert result.playbook_id == "direct-deck-input"

    def test_primitive_slides_preserved_in_deck_definition(self):
        result = generate_presentation(self.PRIMITIVE_SLIDES_YAML)
        slides = result.deck_definition["slides"]
        assert slides[1]["primitive"] == "bullet_slide"

    def test_primitive_slide_content_preserved(self):
        result = generate_presentation(self.PRIMITIVE_SLIDES_YAML)
        slides = result.deck_definition["slides"]
        assert slides[1]["content"]["title"] == "Key Results"

    def test_no_raw_primitive_lines_as_bullet_text(self):
        result = generate_presentation(self.PRIMITIVE_SLIDES_YAML)
        for slide in result.deck_definition.get("slides", []):
            for bullet in slide.get("bullets", []):
                assert "primitive:" not in bullet
                assert "theme:" not in bullet

    FULL_PRIMITIVE_DECK_YAML = textwrap.dedent("""\
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

    def test_top_level_primitive_and_theme_preserved(self):
        result = generate_presentation(self.FULL_PRIMITIVE_DECK_YAML)
        assert result.deck_definition.get("primitive") == "title_slide"
        assert result.deck_definition.get("theme") == "executive"

    def test_stage_is_deck_planned(self):
        result = generate_presentation(self.PRIMITIVE_SLIDES_YAML)
        assert result.stage == "deck_planned"
