"""Pydantic models for all supported pptgen slide types.

Supported types (Phase 1):
    title, section, bullets, two_column, metric_summary, image_caption

All models use extra='forbid' so unknown YAML fields produce a ParseError
rather than being silently ignored.  This enforces the lowercase_snake_case
field contract from the Deck YAML Schema Specification.

The SlideUnion discriminated union dispatches on the `type` field literal,
which means an unrecognised type value (e.g. "chart") raises a clear error
at parse time instead of failing silently.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared base for all slide models
# ---------------------------------------------------------------------------

class _SlideBase(BaseModel):
    """Common optional fields shared by every slide type."""

    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    notes: str | None = None
    visible: bool = True


# ---------------------------------------------------------------------------
# Metric helper model
# ---------------------------------------------------------------------------

class MetricItem(BaseModel):
    """A single metric within a metric_summary slide.

    The `value` field is always stored as a string.  If the YAML author
    writes an unquoted number (e.g. ``value: 99.9``) PyYAML parses it as a
    float.  The field_validator coerces it to a string so the model accepts
    it; the validator layer emits a warning when it detects this happened.
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    unit: str | None = None

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value_to_string(cls, v: Any) -> Any:
        # bool must be checked before int because bool is a subclass of int
        if isinstance(v, bool):
            return str(v).lower()
        if isinstance(v, (int, float)):
            return str(v)
        return v


# ---------------------------------------------------------------------------
# Slide type models
# ---------------------------------------------------------------------------

class TitleSlide(_SlideBase):
    """Opening title slide.

    Schema: type, title, subtitle (all required).
    """

    type: Literal["title"]
    title: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)


class SectionSlide(_SlideBase):
    """Section divider slide.

    Schema: type, section_title (required); section_subtitle (optional).
    """

    type: Literal["section"]
    section_title: str = Field(min_length=1)
    section_subtitle: str | None = None


class BulletsSlide(_SlideBase):
    """Standard content slide with a bullet list.

    Schema: type, title, bullets (all required); bullets must be non-empty.
    Validator emits a warning when bullet count exceeds 6.
    """

    type: Literal["bullets"]
    title: str = Field(min_length=1)
    bullets: list[str] = Field(min_length=1)


class TwoColumnSlide(_SlideBase):
    """Side-by-side comparison slide.

    Schema: type, title, left_content, right_content (all required);
    each content column must contain at least one item.
    """

    type: Literal["two_column"]
    title: str = Field(min_length=1)
    left_content: list[str] = Field(min_length=1)
    right_content: list[str] = Field(min_length=1)


class MetricSummarySlide(_SlideBase):
    """KPI / metric overview slide.

    Schema: type, title, metrics (all required).

    Phase 1 contract:
    - metrics must contain 1–4 items (max enforced by the validator, not
      here, so violations produce a ValidationResult.FAIL with a clear
      message rather than a ParseError).
    - MetricItem.value is always a string; numeric values are coerced.
    - MetricItem.unit is concatenated directly onto value during rendering.

    Template placeholder contract (9 placeholders):
        TITLE
        METRIC_1_LABEL / METRIC_1_VALUE
        METRIC_2_LABEL / METRIC_2_VALUE
        METRIC_3_LABEL / METRIC_3_VALUE
        METRIC_4_LABEL / METRIC_4_VALUE
    """

    type: Literal["metric_summary"]
    title: str = Field(min_length=1)
    metrics: list[MetricItem] = Field(min_length=1)


class ImageCaptionSlide(_SlideBase):
    """Image with caption slide.

    Schema: type, title, image_path, caption (all required).
    """

    type: Literal["image_caption"]
    title: str = Field(min_length=1)
    image_path: str = Field(min_length=1)
    caption: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# Discriminated union — the single type used by DeckFile.slides
# ---------------------------------------------------------------------------

SlideUnion = Annotated[
    Union[
        TitleSlide,
        SectionSlide,
        BulletsSlide,
        TwoColumnSlide,
        MetricSummarySlide,
        ImageCaptionSlide,
    ],
    Field(discriminator="type"),
]
