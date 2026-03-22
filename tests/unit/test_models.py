"""Unit tests for pptgen Pydantic models.

Tests validate model parsing behaviour directly via model_validate(), which
is the layer tested here (not the YAML loader, not the validator).

Scenarios covered:
  - each slide type parses valid input correctly
  - required field absence raises ValidationError
  - empty required arrays raise ValidationError
  - unknown fields raise ValidationError (extra='forbid')
  - MetricItem coerces float and int values to strings
  - MetricItem coerces bool values to strings
  - DeckMetadata coerces float version to string
  - DeckFile rejects extra top-level keys
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pptgen.models.deck import DeckFile, DeckMetadata
from pptgen.models.slides import (
    BulletsSlide,
    ImageCaptionSlide,
    MetricItem,
    MetricSummarySlide,
    SectionSlide,
    TitleSlide,
    TwoColumnSlide,
)


# ---------------------------------------------------------------------------
# DeckMetadata
# ---------------------------------------------------------------------------

class TestDeckMetadata:
    def test_valid_metadata(self):
        m = DeckMetadata.model_validate(
            {"title": "My Deck", "template": "ops_review_v1", "author": "Alice"}
        )
        assert m.title == "My Deck"
        assert m.template == "ops_review_v1"
        assert m.author == "Alice"

    def test_optional_fields_default_to_none(self):
        m = DeckMetadata.model_validate(
            {"title": "T", "template": "tmpl", "author": "A"}
        )
        assert m.subtitle is None
        assert m.version is None
        assert m.date is None
        assert m.status is None
        assert m.tags == []

    def test_float_version_coerced_to_string(self):
        m = DeckMetadata.model_validate(
            {"title": "T", "template": "tmpl", "author": "A", "version": 1.0}
        )
        assert m.version == "1.0"

    def test_int_version_coerced_to_string(self):
        m = DeckMetadata.model_validate(
            {"title": "T", "template": "tmpl", "author": "A", "version": 2}
        )
        assert m.version == "2"

    def test_missing_title_raises(self):
        with pytest.raises(ValidationError, match="title"):
            DeckMetadata.model_validate({"template": "tmpl", "author": "A"})

    def test_empty_title_raises(self):
        with pytest.raises(ValidationError):
            DeckMetadata.model_validate(
                {"title": "", "template": "tmpl", "author": "A"}
            )

    def test_missing_template_raises(self):
        with pytest.raises(ValidationError, match="template"):
            DeckMetadata.model_validate({"title": "T", "author": "A"})

    def test_missing_author_raises(self):
        with pytest.raises(ValidationError, match="author"):
            DeckMetadata.model_validate({"title": "T", "template": "tmpl"})

    def test_unknown_field_raises(self):
        with pytest.raises(ValidationError, match="Extra inputs"):
            DeckMetadata.model_validate(
                {
                    "title": "T",
                    "template": "tmpl",
                    "author": "A",
                    "unknown_key": "value",
                }
            )


# ---------------------------------------------------------------------------
# TitleSlide
# ---------------------------------------------------------------------------

class TestTitleSlide:
    def test_valid_title_slide(self):
        s = TitleSlide.model_validate(
            {"type": "title", "title": "My Title", "subtitle": "My Subtitle"}
        )
        assert s.type == "title"
        assert s.title == "My Title"
        assert s.subtitle == "My Subtitle"

    def test_optional_fields_default(self):
        s = TitleSlide.model_validate(
            {"type": "title", "title": "T", "subtitle": "S"}
        )
        assert s.id is None
        assert s.visible is True

    def test_missing_subtitle_raises(self):
        with pytest.raises(ValidationError, match="subtitle"):
            TitleSlide.model_validate({"type": "title", "title": "T"})

    def test_unknown_field_raises(self):
        with pytest.raises(ValidationError, match="Extra inputs"):
            TitleSlide.model_validate(
                {"type": "title", "title": "T", "subtitle": "S", "foo": "bar"}
            )


# ---------------------------------------------------------------------------
# SectionSlide
# ---------------------------------------------------------------------------

class TestSectionSlide:
    def test_valid_section_slide(self):
        s = SectionSlide.model_validate(
            {"type": "section", "section_title": "My Section"}
        )
        assert s.section_title == "My Section"
        assert s.section_subtitle is None

    def test_with_optional_subtitle(self):
        s = SectionSlide.model_validate(
            {
                "type": "section",
                "section_title": "Section A",
                "section_subtitle": "Overview",
            }
        )
        assert s.section_subtitle == "Overview"

    def test_missing_section_title_raises(self):
        with pytest.raises(ValidationError, match="section_title"):
            SectionSlide.model_validate({"type": "section"})


# ---------------------------------------------------------------------------
# BulletsSlide
# ---------------------------------------------------------------------------

class TestBulletsSlide:
    def test_valid_bullets_slide(self):
        s = BulletsSlide.model_validate(
            {
                "type": "bullets",
                "title": "Key Points",
                "bullets": ["Point A", "Point B"],
            }
        )
        assert s.title == "Key Points"
        assert s.bullets == ["Point A", "Point B"]

    def test_empty_bullets_raises(self):
        with pytest.raises(ValidationError):
            BulletsSlide.model_validate(
                {"type": "bullets", "title": "T", "bullets": []}
            )

    def test_missing_bullets_raises(self):
        with pytest.raises(ValidationError, match="bullets"):
            BulletsSlide.model_validate({"type": "bullets", "title": "T"})

    def test_unknown_field_name_raises(self):
        """bullet_list is the documented wrong field name; must be rejected."""
        with pytest.raises(ValidationError, match="Extra inputs"):
            BulletsSlide.model_validate(
                {
                    "type": "bullets",
                    "title": "T",
                    "bullet_list": ["A"],  # wrong field name
                }
            )


# ---------------------------------------------------------------------------
# TwoColumnSlide
# ---------------------------------------------------------------------------

class TestTwoColumnSlide:
    def test_valid_two_column_slide(self):
        s = TwoColumnSlide.model_validate(
            {
                "type": "two_column",
                "title": "Comparison",
                "left_content": ["Before"],
                "right_content": ["After"],
            }
        )
        assert s.left_content == ["Before"]
        assert s.right_content == ["After"]

    def test_empty_left_column_raises(self):
        with pytest.raises(ValidationError):
            TwoColumnSlide.model_validate(
                {
                    "type": "two_column",
                    "title": "T",
                    "left_content": [],
                    "right_content": ["After"],
                }
            )

    def test_missing_right_column_raises(self):
        with pytest.raises(ValidationError, match="right_content"):
            TwoColumnSlide.model_validate(
                {
                    "type": "two_column",
                    "title": "T",
                    "left_content": ["Before"],
                }
            )


# ---------------------------------------------------------------------------
# MetricItem
# ---------------------------------------------------------------------------

class TestMetricItem:
    def test_valid_string_value(self):
        m = MetricItem.model_validate({"label": "Rate", "value": "98%"})
        assert m.value == "98%"

    def test_float_value_coerced_to_string(self):
        m = MetricItem.model_validate({"label": "Rate", "value": 99.9})
        assert m.value == "99.9"

    def test_int_value_coerced_to_string(self):
        m = MetricItem.model_validate({"label": "Count", "value": 1200})
        assert m.value == "1200"

    def test_bool_value_coerced_to_string(self):
        m = MetricItem.model_validate({"label": "Flag", "value": True})
        assert m.value == "true"

    def test_unit_optional(self):
        m = MetricItem.model_validate({"label": "Rate", "value": "99%"})
        assert m.unit is None

    def test_unit_present(self):
        m = MetricItem.model_validate({"label": "Latency", "value": "320", "unit": " ms"})
        assert m.unit == " ms"

    def test_missing_label_raises(self):
        with pytest.raises(ValidationError, match="label"):
            MetricItem.model_validate({"value": "99%"})

    def test_empty_label_raises(self):
        with pytest.raises(ValidationError):
            MetricItem.model_validate({"label": "", "value": "99%"})

    def test_missing_value_raises(self):
        with pytest.raises(ValidationError, match="value"):
            MetricItem.model_validate({"label": "Rate"})

    def test_unknown_field_raises(self):
        with pytest.raises(ValidationError, match="Extra inputs"):
            MetricItem.model_validate(
                {"label": "Rate", "value": "99%", "description": "unused"}
            )


# ---------------------------------------------------------------------------
# MetricSummarySlide
# ---------------------------------------------------------------------------

class TestMetricSummarySlide:
    def _metric(self, label: str, value: str) -> dict:
        return {"label": label, "value": value}

    def test_valid_metric_summary(self):
        s = MetricSummarySlide.model_validate(
            {
                "type": "metric_summary",
                "title": "KPI Snapshot",
                "metrics": [
                    self._metric("Rate", "98%"),
                    self._metric("Volume", "1.2M"),
                ],
            }
        )
        assert s.title == "KPI Snapshot"
        assert len(s.metrics) == 2

    def test_four_metrics_accepted(self):
        s = MetricSummarySlide.model_validate(
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [self._metric(f"M{i}", str(i)) for i in range(4)],
            }
        )
        assert len(s.metrics) == 4

    def test_five_metrics_accepted_by_model(self):
        # Max-4 is enforced by the validator, NOT by the model.
        # The model accepts 5 metrics so the validator can return a FAIL
        # result with a meaningful message rather than raising ParseError.
        s = MetricSummarySlide.model_validate(
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [self._metric(f"M{i}", str(i)) for i in range(5)],
            }
        )
        assert len(s.metrics) == 5

    def test_empty_metrics_raises(self):
        with pytest.raises(ValidationError):
            MetricSummarySlide.model_validate(
                {"type": "metric_summary", "title": "T", "metrics": []}
            )

    def test_missing_metrics_raises(self):
        with pytest.raises(ValidationError, match="metrics"):
            MetricSummarySlide.model_validate(
                {"type": "metric_summary", "title": "T"}
            )


# ---------------------------------------------------------------------------
# ImageCaptionSlide
# ---------------------------------------------------------------------------

class TestImageCaptionSlide:
    def test_valid_image_caption_slide(self):
        s = ImageCaptionSlide.model_validate(
            {
                "type": "image_caption",
                "title": "Architecture",
                "image_path": "assets/arch.png",
                "caption": "System overview",
            }
        )
        assert s.image_path == "assets/arch.png"
        assert s.caption == "System overview"

    def test_missing_caption_raises(self):
        with pytest.raises(ValidationError, match="caption"):
            ImageCaptionSlide.model_validate(
                {
                    "type": "image_caption",
                    "title": "T",
                    "image_path": "assets/img.png",
                }
            )


# ---------------------------------------------------------------------------
# DeckFile — discriminated union behaviour
# ---------------------------------------------------------------------------

class TestDeckFile:
    def _minimal_deck(self, slide: dict) -> dict:
        return {
            "deck": {"title": "T", "template": "tmpl", "author": "A"},
            "slides": [slide],
        }

    def test_valid_deck_parses(self):
        d = DeckFile.model_validate(
            self._minimal_deck(
                {"type": "title", "title": "Hello", "subtitle": "World"}
            )
        )
        assert d.deck.title == "T"
        assert isinstance(d.slides[0], TitleSlide)

    def test_unsupported_slide_type_raises(self):
        with pytest.raises(ValidationError):
            DeckFile.model_validate(
                self._minimal_deck({"type": "chart", "title": "T"})
            )

    def test_extra_top_level_key_raises(self):
        data = self._minimal_deck({"type": "title", "title": "T", "subtitle": "S"})
        data["extra_key"] = "not allowed"
        with pytest.raises(ValidationError, match="Extra inputs"):
            DeckFile.model_validate(data)

    def test_empty_slides_array_raises(self):
        with pytest.raises(ValidationError):
            DeckFile.model_validate(
                {"deck": {"title": "T", "template": "tmpl", "author": "A"}, "slides": []}
            )
