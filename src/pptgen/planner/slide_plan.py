"""SlidePlan model — structured planning output from the slide planner.

A SlidePlan is the lightweight intermediate representation produced by
``plan_slides()``.  It describes *what* the deck will contain without
duplicating the full deck YAML structure.  It is useful for:

- observability / debugging (what did the planner decide?)
- future CLI summary output
- unit testing the planner in isolation from the renderer
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlannedSlide:
    """A single planned slide entry.

    Attributes:
        slide_type:           Slide type string (e.g. ``"title"``, ``"bullets"``).
        title:                Slide title derived from the spec.
        source_section_title: Title of the SectionSpec that produced this slide,
                              or ``None`` for the title slide.
    """

    slide_type: str
    title: str
    source_section_title: str | None = None


@dataclass
class SlidePlan:
    """Planning summary for a full presentation.

    Attributes:
        playbook_id:          Playbook that produced the source spec, or ``None``
                              if not known.
        slide_count:          Total number of planned slides.
        planned_slide_types:  Ordered list of slide type strings (mirrors
                              ``slides`` but without per-slide details).
        section_count:        Number of sections in the source PresentationSpec.
        slides:               Per-slide planning entries.
        notes:                Optional diagnostic notes set by the planner.
    """

    playbook_id: str | None
    slide_count: int
    planned_slide_types: list[str]
    section_count: int
    slides: list[PlannedSlide] = field(default_factory=list)
    notes: str = ""
