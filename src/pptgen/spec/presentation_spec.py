"""Presentation spec models.

A PresentationSpec describes the **semantic content** of a presentation,
not its slide layout.  Authors (human or AI) describe what they want to
communicate; the spec-to-deck translator decides which slide types to use.

Design principles
-----------------
- Fields map to communication intent, not template placeholders.
- All fields have sensible defaults so minimal specs are valid.
- Pydantic ``extra='forbid'`` enforces the schema contract.
- This layer has no dependency on the renderer or template layer.

Typical spec hierarchy::

    PresentationSpec
      title
      subtitle
      author
      template
      sections[]
        SectionSpec
          title
          bullets[]
          metrics[]
            MetricSpec
          images[]
            ImageSpec
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MetricSpec(BaseModel):
    """A single metric to display in a metrics grid.

    Attributes:
        label: Short metric name (≤40 characters recommended).
        value: Metric value as a string (e.g. "99.2%", "14").
        unit:  Optional unit suffix appended to value (e.g. " ms", "%").
               Include a leading space if a separator is desired.
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    unit: str | None = None


class ImageSpec(BaseModel):
    """An image or diagram to include in a section.

    Attributes:
        path:    Relative or absolute path to the image file (PNG or JPEG).
        caption: Explanatory text displayed below or beside the image.
        title:   Optional override for the slide title. Defaults to the
                 parent section title if not set.
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    caption: str = Field(min_length=1)
    title: str | None = None


class SectionSpec(BaseModel):
    """Semantic description of one section of a presentation.

    A section can contain any combination of bullets, metrics, and images.
    The translator decides how many slides to generate based on the content.

    Attributes:
        title:   Section heading.
        bullets: Bulleted content items (max 6 per generated slide).
        metrics: KPI/metric values (max 4 per generated metric_summary slide).
        images:  Diagrams or screenshots (one image_caption slide each).
        include_section_divider: When True (default), emit a section slide
                 before the section content slides.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    bullets: list[str] = Field(default_factory=list)
    metrics: list[MetricSpec] = Field(default_factory=list)
    images: list[ImageSpec] = Field(default_factory=list)
    include_section_divider: bool = True


class PresentationSpec(BaseModel):
    """Top-level semantic description of a full presentation.

    Attributes:
        title:    Presentation title.
        subtitle: Presentation subtitle or context line.
        author:   Author name (written to deck metadata).
        template: pptgen template ID (must be registered in templates/registry.yaml).
        sections: Ordered list of presentation sections.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    subtitle: str = Field(min_length=1)
    author: str = "Unknown"
    template: str = "ops_review_v1"
    sections: list[SectionSpec] = Field(default_factory=list)
