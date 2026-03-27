"""Regression tests for Phase 9 structured deck shape validation.

The guardrail: _validate_structured_deck_shape() is called immediately after
_try_parse_deck_definition() succeeds, before any Phase 9 resolution stage runs.
This converts downstream TypeError/AttributeError failures into PipelineError
(HTTP 400) so callers receive a user-facing error, not a 500.

Covers:
- Unknown top-level key raises PipelineError (orphan block regression)
- Multiple unknown keys all appear in error message
- Empty slides list raises PipelineError
- Non-dict slide raises PipelineError (with slide index and type name)
- Slide missing both type and primitive raises PipelineError
- Valid legacy shape passes validation
- Valid Phase 9 root shape passes validation (all allowed meta fields)
- Valid mixed legacy + primitive slides pass validation
- All _ALLOWED_STRUCTURED_DECK_KEYS pass validation
- generate_presentation() surfaces unknown key as PipelineError (not TypeError)
- generate_presentation() surfaces empty slides as PipelineError
- generate_presentation() surfaces non-dict slide as PipelineError
- generate_presentation() surfaces slide without type/primitive as PipelineError
- Narrative text is not affected by validation (not parsed as structured deck)
"""
from __future__ import annotations

import textwrap

import pytest

from pptgen.pipeline.generation_pipeline import (
    PipelineError,
    _validate_structured_deck_shape,
    generate_presentation,
)


# ---------------------------------------------------------------------------
# TestValidateStructuredDeckShape — unit tests for the validation helper
# ---------------------------------------------------------------------------


class TestValidateStructuredDeckShape:
    # ------------------------------------------------------------------ #
    # Unknown top-level keys                                               #
    # ------------------------------------------------------------------ #

    def test_unknown_top_level_key_raises(self):
        data = {
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
            "icon": {"asset_id": "icon.check"},
        }
        with pytest.raises(PipelineError, match="unexpected top-level key"):
            _validate_structured_deck_shape(data)

    def test_unknown_key_name_in_error_message(self):
        data = {
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
            "component": {"name": "header"},
        }
        with pytest.raises(PipelineError, match="component"):
            _validate_structured_deck_shape(data)

    def test_multiple_unknown_keys_all_reported(self):
        data = {
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
            "icon": {},
            "widget": {},
        }
        exc = pytest.raises(PipelineError, match="unexpected top-level key")
        with exc as info:
            _validate_structured_deck_shape(data)
        msg = str(info.value)
        assert "icon" in msg
        assert "widget" in msg

    # ------------------------------------------------------------------ #
    # Empty slides list                                                    #
    # ------------------------------------------------------------------ #

    def test_empty_slides_list_raises(self):
        data = {"title": "T", "slides": []}
        with pytest.raises(PipelineError, match="empty 'slides' list"):
            _validate_structured_deck_shape(data)

    # ------------------------------------------------------------------ #
    # Non-dict slides                                                      #
    # ------------------------------------------------------------------ #

    def test_scalar_slide_raises(self):
        data = {"slides": ["just a string"]}
        with pytest.raises(PipelineError, match="slide 0 is not a mapping"):
            _validate_structured_deck_shape(data)

    def test_scalar_slide_reports_type(self):
        data = {"slides": [42]}
        with pytest.raises(PipelineError, match="int"):
            _validate_structured_deck_shape(data)

    def test_list_slide_raises(self):
        data = {"slides": [["key", "val"]]}
        with pytest.raises(PipelineError, match="slide 0 is not a mapping"):
            _validate_structured_deck_shape(data)

    def test_non_dict_slide_reports_index(self):
        data = {
            "slides": [
                {"type": "title", "title": "T", "subtitle": "S"},
                "oops",
            ]
        }
        with pytest.raises(PipelineError, match="slide 1"):
            _validate_structured_deck_shape(data)

    # ------------------------------------------------------------------ #
    # Slide missing type and primitive                                     #
    # ------------------------------------------------------------------ #

    def test_slide_without_type_or_primitive_raises(self):
        data = {"slides": [{"title": "T", "subtitle": "S"}]}
        with pytest.raises(PipelineError, match="neither 'type' nor 'primitive'"):
            _validate_structured_deck_shape(data)

    def test_slide_without_type_or_primitive_reports_index(self):
        data = {
            "slides": [
                {"type": "title", "title": "T", "subtitle": "S"},
                {"content": {"title": "Orphan"}},
            ]
        }
        with pytest.raises(PipelineError, match="slide 1"):
            _validate_structured_deck_shape(data)

    # ------------------------------------------------------------------ #
    # Valid shapes — must not raise                                        #
    # ------------------------------------------------------------------ #

    def test_valid_legacy_shape_passes(self):
        data = {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        _validate_structured_deck_shape(data)  # no exception

    def test_valid_phase9_root_shape_passes(self):
        data = {
            "title": "My Deck",
            "theme": "executive",
            "slides": [{"primitive": "title_slide", "content": {"title": "T"}}],
        }
        _validate_structured_deck_shape(data)  # no exception

    def test_valid_all_allowed_meta_fields_pass(self):
        data = {
            "title": "T",
            "subtitle": "S",
            "author": "A",
            "template": "ops_review_v1",
            "version": "1.0",
            "date": "2026-01-01",
            "status": "draft",
            "description": "Desc",
            "tags": ["ops"],
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        _validate_structured_deck_shape(data)  # no exception

    def test_valid_phase9_resolution_fields_pass(self):
        data = {
            "primitive": "bullet_slide",
            "theme": "executive",
            "content": {"title": "T"},
            "layout": "single_column",
            "slots": {"content": "T"},
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        _validate_structured_deck_shape(data)  # no exception

    def test_valid_mixed_slides_pass(self):
        data = {
            "slides": [
                {"type": "title", "title": "T", "subtitle": "S"},
                {"primitive": "bullet_slide", "content": {"title": "Q3"}},
                {"type": "bullets", "title": "R", "bullets": ["a"]},
            ]
        }
        _validate_structured_deck_shape(data)  # no exception


# ---------------------------------------------------------------------------
# TestGeneratePresentationValidation — integration: malformed YAML → PipelineError
# ---------------------------------------------------------------------------


class TestGeneratePresentationValidation:
    """generate_presentation() must surface validation errors as PipelineError,
    not as TypeError/AttributeError (which would produce HTTP 500)."""

    def test_orphan_top_level_key_raises_pipeline_error(self):
        yaml_orphan = textwrap.dedent("""\
            title: "DevOps Platform"
            slides:
              - type: title
                title: "Platform"
                subtitle: "Overview"
            icon:
              asset_id: icon.check
        """)
        with pytest.raises(PipelineError, match="unexpected top-level key"):
            generate_presentation(yaml_orphan)

    def test_empty_slides_raises_pipeline_error(self):
        yaml_empty = textwrap.dedent("""\
            title: "Empty Deck"
            slides: []
        """)
        with pytest.raises(PipelineError, match="empty 'slides' list"):
            generate_presentation(yaml_empty)

    def test_non_dict_slide_raises_pipeline_error(self):
        yaml_bad_slide = textwrap.dedent("""\
            title: "Bad Deck"
            slides:
              - type: title
                title: "OK"
                subtitle: "Fine"
              - "just a string"
        """)
        with pytest.raises(PipelineError, match="not a mapping"):
            generate_presentation(yaml_bad_slide)

    def test_slide_without_type_or_primitive_raises_pipeline_error(self):
        yaml_orphan_slide = textwrap.dedent("""\
            title: "Orphan Slide"
            slides:
              - title: "No type key here"
                content: "Something"
        """)
        with pytest.raises(PipelineError, match="neither 'type' nor 'primitive'"):
            generate_presentation(yaml_orphan_slide)

    def test_multiple_unknown_keys_raises_pipeline_error(self):
        yaml_multi_unknown = textwrap.dedent("""\
            title: "Multi Bad"
            slides:
              - type: title
                title: "T"
                subtitle: "S"
            icon: {}
            widget: {}
        """)
        with pytest.raises(PipelineError, match="unexpected top-level key"):
            generate_presentation(yaml_multi_unknown)

    def test_narrative_text_not_affected(self):
        """Narrative text is not YAML with a slides list — bypass not triggered."""
        narrative = (
            "We need to improve our CI/CD pipeline. "
            "The deployment frequency is too low and teams are blocked."
        )
        # Should not raise PipelineError from validation (may raise for other reasons)
        # — just confirm it does not raise the validation error.
        try:
            generate_presentation(narrative)
        except PipelineError as exc:
            assert "unexpected top-level key" not in str(exc)
            assert "empty 'slides' list" not in str(exc)
            assert "not a mapping" not in str(exc)
            assert "neither 'type' nor 'primitive'" not in str(exc)

    def test_valid_phase9_deck_still_succeeds(self):
        """The original failing shape now succeeds end-to-end (regression guard)."""
        yaml_valid = textwrap.dedent("""\
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
        """)
        result = generate_presentation(yaml_valid)
        assert result.stage == "deck_planned"
        assert result.playbook_id == "direct-deck-input"

    def test_valid_legacy_deck_still_succeeds(self):
        yaml_legacy = textwrap.dedent("""\
            deck:
              title: "Legacy Deck"
              template: "ops_review_v1"
              author: "Team"
            slides:
              - type: title
                id: slide-1
                title: "Legacy Deck"
                subtitle: "Overview"
                notes: null
                visible: true
        """)
        result = generate_presentation(yaml_legacy)
        assert result.stage == "deck_planned"
        assert result.playbook_id == "direct-deck-input"
