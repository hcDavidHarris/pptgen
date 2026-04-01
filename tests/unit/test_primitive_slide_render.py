"""Regression tests for Phase 9 primitive-slide pre-render normalisation.

Root cause: render_deck() called slide_model.type on PrimitiveSlide instances,
which have no .type attribute, raising AttributeError → HTTP 500.

Fix: _normalize_primitive_slides() converts per-slide primitive: dicts to
their legacy type: equivalents immediately before parse_deck() in _render().

Covers:
- _normalize_primitive_slides: fast-path when no primitive slides present
- _normalize_primitive_slides: converts each known primitive to legacy type
- _primitive_slide_to_legacy: title_slide maps to type=title
- _primitive_slide_to_legacy: section_slide maps to type=section
- _primitive_slide_to_legacy: bullet_slide maps to type=bullets
- _primitive_slide_to_legacy: comparison_slide flat fields map to two_column
- _primitive_slide_to_legacy: comparison_slide nested fields map to two_column
- _primitive_slide_to_legacy: metrics_slide strips extra fields (e.g. icon)
- _primitive_slide_to_legacy: image_text_slide uses resolved_source for image_path
- _primitive_slide_to_legacy: unknown primitive falls back to title slide
- _primitive_slide_to_legacy: subtitle defaults to space when absent (min_length=1)
- _primitive_slide_to_legacy: bullet list defaults to ["(no content)"] when empty
- _primitive_slide_to_legacy: two_column lists default to ["—"] when empty
- _primitive_slide_to_legacy: metrics default to label/value placeholder when empty
- _primitive_slide_to_legacy: base bookkeeping fields (id, notes, visible) preserved
- generate_presentation (render): exact failing YAML succeeds without HTTP 500
- generate_presentation (render): all 5 primitive types produce a valid .pptx
- generate_presentation (render): legacy deck still renders correctly
- generate_presentation (render): mixed primitive+legacy deck renders correctly
- generate_presentation (preview): still works as before (no regression)
"""
from __future__ import annotations

import os
import tempfile
import textwrap

import pytest

from pptgen.pipeline.generation_pipeline import (
    _normalize_primitive_slides,
    _primitive_slide_to_legacy,
    generate_presentation,
)


# ---------------------------------------------------------------------------
# TestNormalizePrimitiveSlides — unit tests for the normalization helper
# ---------------------------------------------------------------------------


class TestNormalizePrimitiveSlides:
    def test_fast_path_no_primitive_slides(self):
        data = {
            "deck": {"title": "T", "template": "ops_review_v1", "author": "A"},
            "slides": [{"type": "title", "title": "T", "subtitle": "S"}],
        }
        result = _normalize_primitive_slides(data)
        assert result is data  # exact same object — not copied

    def test_no_slides_key_returns_unchanged(self):
        data = {"deck": {"title": "T"}}
        result = _normalize_primitive_slides(data)
        assert result is data

    def test_converts_primitive_slide_in_list(self):
        data = {
            "slides": [{"primitive": "title_slide", "content": {"title": "T", "subtitle": "S"}}]
        }
        result = _normalize_primitive_slides(data)
        assert result["slides"][0]["type"] == "title"
        assert "primitive" not in result["slides"][0]

    def test_passes_through_legacy_slides_unchanged(self):
        legacy = {"type": "bullets", "title": "T", "bullets": ["a"]}
        data = {"slides": [legacy]}
        result = _normalize_primitive_slides(data)
        assert result["slides"][0] is legacy

    def test_mixed_deck_converts_only_primitive_slides(self):
        legacy = {"type": "title", "title": "T", "subtitle": "S"}
        prim = {"primitive": "bullet_slide", "content": {"title": "B", "bullets": ["x"]}}
        data = {"slides": [legacy, prim]}
        result = _normalize_primitive_slides(data)
        assert result["slides"][0] is legacy
        assert result["slides"][1]["type"] == "bullets"

    def test_top_level_keys_preserved(self):
        data = {
            "title": "My Deck",
            "theme": "executive",
            "slides": [{"primitive": "title_slide", "content": {"title": "T", "subtitle": "S"}}],
        }
        result = _normalize_primitive_slides(data)
        assert result["title"] == "My Deck"
        assert result["theme"] == "executive"


# ---------------------------------------------------------------------------
# TestPrimitiveSlideToLegacy — unit tests for each primitive mapping
# ---------------------------------------------------------------------------


class TestPrimitiveSlideToLegacy:
    # ------------------------------------------------------------------ #
    # title_slide                                                          #
    # ------------------------------------------------------------------ #

    def test_title_slide_type(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "content": {"title": "T", "subtitle": "S"}}
        )
        assert s["type"] == "title"

    def test_title_slide_fields(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "content": {"title": "My Title", "subtitle": "My Sub"}}
        )
        assert s["title"] == "My Title"
        assert s["subtitle"] == "My Sub"

    def test_title_slide_subtitle_defaults_to_space_when_absent(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "content": {"title": "T"}}
        )
        assert len(s["subtitle"]) >= 1  # must satisfy min_length=1

    # ------------------------------------------------------------------ #
    # section_slide                                                        #
    # ------------------------------------------------------------------ #

    def test_section_slide_type(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "section_slide", "content": {"heading": "Phase 2"}}
        )
        assert s["type"] == "section"

    def test_section_slide_heading_field(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "section_slide", "content": {"heading": "My Section"}}
        )
        assert s["section_title"] == "My Section"

    def test_section_slide_title_fallback(self):
        # heading absent — fall back to title
        s = _primitive_slide_to_legacy(
            {"primitive": "section_slide", "content": {"title": "Fallback"}}
        )
        assert s["section_title"] == "Fallback"

    # ------------------------------------------------------------------ #
    # bullet_slide                                                         #
    # ------------------------------------------------------------------ #

    def test_bullet_slide_type(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "bullet_slide", "content": {"title": "T", "bullets": ["a"]}}
        )
        assert s["type"] == "bullets"

    def test_bullet_slide_fields(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "bullet_slide", "content": {"title": "Points", "bullets": ["x", "y"]}}
        )
        assert s["title"] == "Points"
        assert s["bullets"] == ["x", "y"]

    def test_bullet_slide_empty_bullets_defaults(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "bullet_slide", "content": {"title": "T", "bullets": []}}
        )
        assert len(s["bullets"]) >= 1  # must satisfy min_length=1

    def test_summary_slide_maps_to_bullets(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "summary_slide", "content": {"title": "S", "key_points": ["p"]}}
        )
        assert s["type"] == "bullets"
        assert s["bullets"] == ["p"]

    # ------------------------------------------------------------------ #
    # comparison_slide (flat content shape)                                #
    # ------------------------------------------------------------------ #

    def test_comparison_slide_flat_type(self):
        s = _primitive_slide_to_legacy({"primitive": "comparison_slide", "content": {
            "left_title": "Before", "left_points": ["a"],
            "right_title": "After", "right_points": ["b"],
        }})
        assert s["type"] == "two_column"

    def test_comparison_slide_flat_title_from_left_title(self):
        s = _primitive_slide_to_legacy({"primitive": "comparison_slide", "content": {
            "left_title": "Before", "left_points": ["a"], "right_points": ["b"],
        }})
        assert s["title"] == "Before"

    def test_comparison_slide_flat_left_right_content(self):
        s = _primitive_slide_to_legacy({"primitive": "comparison_slide", "content": {
            "left_title": "A", "left_points": ["x1", "x2"],
            "right_title": "B", "right_points": ["y1"],
        }})
        assert s["left_content"] == ["x1", "x2"]
        assert s["right_content"] == ["y1"]

    def test_comparison_slide_flat_empty_lists_default(self):
        s = _primitive_slide_to_legacy({"primitive": "comparison_slide", "content": {
            "left_title": "A", "left_points": [], "right_points": [],
        }})
        assert len(s["left_content"]) >= 1
        assert len(s["right_content"]) >= 1

    # ------------------------------------------------------------------ #
    # comparison_slide (nested content shape)                             #
    # ------------------------------------------------------------------ #

    def test_comparison_slide_nested_type(self):
        s = _primitive_slide_to_legacy({"primitive": "comparison_slide", "content": {
            "left": {"title": "Before", "bullets": ["old"]},
            "right": {"title": "After", "bullets": ["new"]},
        }})
        assert s["type"] == "two_column"

    def test_comparison_slide_nested_fields(self):
        s = _primitive_slide_to_legacy({"primitive": "comparison_slide", "content": {
            "left": {"title": "L", "bullets": ["a", "b"]},
            "right": {"title": "R", "bullets": ["c"]},
        }})
        assert s["left_content"] == ["a", "b"]
        assert s["right_content"] == ["c"]

    # ------------------------------------------------------------------ #
    # metrics_slide                                                        #
    # ------------------------------------------------------------------ #

    def test_metrics_slide_type(self):
        s = _primitive_slide_to_legacy({"primitive": "metrics_slide", "content": {
            "title": "KPIs",
            "metrics": [{"label": "Uptime", "value": "99%"}],
        }})
        assert s["type"] == "metric_summary"

    def test_metrics_slide_strips_icon_field(self):
        """icon field from asset-resolved metric must be stripped — MetricItem.extra='forbid'."""
        s = _primitive_slide_to_legacy({"primitive": "metrics_slide", "content": {
            "title": "KPIs",
            "metrics": [{"label": "Speed", "value": "2x", "icon": {"asset_id": "icon.check"}}],
        }})
        assert "icon" not in s["metrics"][0]
        assert s["metrics"][0] == {"label": "Speed", "value": "2x"}

    def test_metrics_slide_preserves_unit(self):
        s = _primitive_slide_to_legacy({"primitive": "metrics_slide", "content": {
            "title": "T",
            "metrics": [{"label": "L", "value": "42", "unit": " ms"}],
        }})
        assert s["metrics"][0]["unit"] == " ms"

    def test_metrics_slide_empty_metrics_defaults(self):
        s = _primitive_slide_to_legacy({"primitive": "metrics_slide", "content": {
            "title": "T", "metrics": [],
        }})
        assert len(s["metrics"]) >= 1

    def test_metrics_slide_resolved_asset_icon_stripped(self):
        """icon replaced by asset resolver ({asset_id, resolved_source, ...}) is also stripped."""
        s = _primitive_slide_to_legacy({"primitive": "metrics_slide", "content": {
            "title": "T",
            "metrics": [{
                "label": "Speed", "value": "2x",
                "icon": {"asset_id": "icon.check", "resolved_source": "assets/icons/check.svg",
                         "type": "icon", "version": "1.0.0"},
            }],
        }})
        assert "icon" not in s["metrics"][0]

    # ------------------------------------------------------------------ #
    # image_text_slide                                                     #
    # ------------------------------------------------------------------ #

    def test_image_text_slide_type(self):
        s = _primitive_slide_to_legacy({"primitive": "image_text_slide", "content": {
            "title": "T",
            "image": {"resolved_source": "path/to/img.png"},
            "description": {"text": "Caption text"},
        }})
        assert s["type"] == "image_caption"

    def test_image_text_slide_uses_resolved_source(self):
        s = _primitive_slide_to_legacy({"primitive": "image_text_slide", "content": {
            "title": "T",
            "image": {"asset_id": "logo.company", "resolved_source": "assets/logos/company.svg"},
            "description": {"text": "A caption"},
        }})
        assert s["image_path"] == "assets/logos/company.svg"

    def test_image_text_slide_caption_from_description_text(self):
        s = _primitive_slide_to_legacy({"primitive": "image_text_slide", "content": {
            "title": "T",
            "image": {"resolved_source": "x.png"},
            "description": {"text": "The real caption", "emphasis": "real"},
        }})
        assert s["caption"] == "The real caption"

    # ------------------------------------------------------------------ #
    # unknown primitive                                                    #
    # ------------------------------------------------------------------ #

    def test_unknown_primitive_falls_back_to_title_slide(self):
        s = _primitive_slide_to_legacy({"primitive": "futuristic_hologram", "content": {}})
        assert s["type"] == "title"

    def test_unknown_primitive_uses_primitive_name_as_title(self):
        s = _primitive_slide_to_legacy({"primitive": "futuristic_hologram", "content": {}})
        assert "futuristic_hologram" in s["title"]

    # ------------------------------------------------------------------ #
    # bookkeeping fields                                                   #
    # ------------------------------------------------------------------ #

    def test_id_preserved(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "id": "slide-1", "content": {"title": "T", "subtitle": "S"}}
        )
        assert s["id"] == "slide-1"

    def test_notes_preserved(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "notes": "Speaker notes", "content": {"title": "T"}}
        )
        assert s["notes"] == "Speaker notes"

    def test_visible_false_preserved(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "visible": False, "content": {"title": "T"}}
        )
        assert s["visible"] is False

    def test_visible_defaults_to_true(self):
        s = _primitive_slide_to_legacy(
            {"primitive": "title_slide", "content": {"title": "T"}}
        )
        assert s["visible"] is True


# ---------------------------------------------------------------------------
# TestGeneratePresentationRender — integration: Generate path (with output_path)
# ---------------------------------------------------------------------------


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
          title: "Operational Pain Points"
          bullets:
            - "Manual interventions across pipelines"
            - "Inconsistent deployment patterns"
            - "Limited observability and traceability"

      - primitive: comparison_slide
        content:
          left_title: "Before"
          right_title: "After"
          left_points:
            - "Ad-hoc scripts"
            - "Reactive troubleshooting"
            - "Siloed systems"
          right_points:
            - "Standardized pipelines"
            - "Proactive monitoring"
            - "Unified platform"

      - primitive: metrics_slide
        content:
          title: "Platform Impact"
          metrics:
            - label: "Deployment Time"
              value: "down 45%"
              icon:
                asset_id: icon.check
            - label: "Failure Rate"
              value: "down 30%"
              icon:
                asset_id: icon.warning
            - label: "Client Onboarding"
              value: "down 50%"
              icon:
                asset_id: icon.check

      - primitive: image_text_slide
        content:
          title: "Architecture Direction"
          description:
            text: "The platform composes primitives, layouts, tokens, and assets into a renderer-ready deck."
            emphasis: "renderer-ready deck"
          image:
            asset_id: logo.company
""")


class TestGeneratePresentationRender:
    def test_failing_yaml_no_longer_raises(self):
        """Core regression: the exact failing YAML must produce a .pptx without error."""
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            path = f.name
        try:
            result = generate_presentation(FAILING_YAML, output_path=path)
            assert result.stage == "rendered"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_pptx_file_is_written_and_non_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            path = f.name
        try:
            generate_presentation(FAILING_YAML, output_path=path)
            assert os.path.getsize(path) > 10_000
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_playbook_id_is_direct_deck_input(self):
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            path = f.name
        try:
            result = generate_presentation(FAILING_YAML, output_path=path)
            assert result.playbook_id == "direct-deck-input"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_legacy_deck_still_renders(self):
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
              - type: bullets
                title: "Key Points"
                bullets:
                  - "Point one"
                  - "Point two"
        """)
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            path = f.name
        try:
            result = generate_presentation(yaml_legacy, output_path=path)
            assert result.stage == "rendered"
            assert os.path.getsize(path) > 5_000
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_mixed_primitive_and_legacy_slides_renders(self):
        yaml_mixed = textwrap.dedent("""\
            deck:
              title: "Mixed Deck"
              template: "ops_review_v1"
              author: "Team"
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
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            path = f.name
        try:
            result = generate_presentation(yaml_mixed, output_path=path)
            assert result.stage == "rendered"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def test_preview_still_works(self):
        """Preview path (no output_path) must not be affected."""
        result = generate_presentation(FAILING_YAML)
        assert result.stage == "deck_planned"
        assert result.playbook_id == "direct-deck-input"

    def test_metrics_with_asset_icon_renders_without_validation_error(self):
        """asset-resolved icon fields in metrics must be stripped before MetricItem validation."""
        yaml_metrics = textwrap.dedent("""\
            title: "Metrics Deck"
            slides:
              - primitive: metrics_slide
                content:
                  title: "KPIs"
                  metrics:
                    - label: "Uptime"
                      value: "99.9%"
                      icon:
                        asset_id: icon.check
                    - label: "Latency"
                      value: "42ms"
                      icon:
                        asset_id: icon.warning
        """)
        with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
            path = f.name
        try:
            result = generate_presentation(yaml_metrics, output_path=path)
            assert result.stage == "rendered"
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
