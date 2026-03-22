"""Slide planning engine.

Converts a :class:`~pptgen.spec.presentation_spec.PresentationSpec` into a
:class:`~pptgen.planner.slide_plan.SlidePlan` that describes the intended
slide structure before any rendering occurs.

Design constraints
------------------
- Deterministic: same spec always produces the same plan.
- No external calls, no randomness.
- Thresholds sourced exclusively from :mod:`planning_rules`.
- Does *not* duplicate the deck-dict conversion logic in ``spec_to_deck``;
  the pipeline calls ``convert_spec_to_deck()`` separately to produce the
  full deck definition.
"""

from __future__ import annotations

import math

from ..spec.presentation_spec import PresentationSpec, SectionSpec
from .planning_rules import MAX_BULLETS_PER_SLIDE, MAX_METRICS_PER_SLIDE
from .slide_plan import PlannedSlide, SlidePlan


def plan_slides(
    spec: PresentationSpec,
    playbook_id: str | None = None,
) -> SlidePlan:
    """Produce a deterministic :class:`SlidePlan` from *spec*.

    Args:
        spec:        A validated :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
        playbook_id: Optional playbook identifier recorded in the plan for
                     observability.

    Returns:
        A :class:`SlidePlan` whose ``slide_count`` and ``planned_slide_types``
        reflect every slide the translator will emit.

    Raises:
        TypeError: If *spec* is not a :class:`PresentationSpec`.
    """
    if not isinstance(spec, PresentationSpec):
        raise TypeError(
            f"plan_slides() expects a PresentationSpec, got {type(spec).__name__!r}."
        )

    planned: list[PlannedSlide] = []

    # Title slide is always first
    planned.append(PlannedSlide(slide_type="title", title=spec.title))

    if spec.sections:
        for section in spec.sections:
            _plan_section(section, planned)
    else:
        # Minimal fallback: one overview content slide so no deck is slide-less
        planned.append(
            PlannedSlide(slide_type="bullets", title="Overview")
        )

    slide_types = [s.slide_type for s in planned]

    return SlidePlan(
        playbook_id=playbook_id,
        slide_count=len(planned),
        planned_slide_types=slide_types,
        section_count=len(spec.sections),
        slides=planned,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _plan_section(section: SectionSpec, planned: list[PlannedSlide]) -> None:
    """Append :class:`PlannedSlide` entries for one *section*."""

    if section.include_section_divider:
        planned.append(
            PlannedSlide(
                slide_type="section",
                title=section.title,
                source_section_title=section.title,
            )
        )

    if section.bullets:
        n_slides = math.ceil(len(section.bullets) / MAX_BULLETS_PER_SLIDE)
        for _ in range(n_slides):
            planned.append(
                PlannedSlide(
                    slide_type="bullets",
                    title=section.title,
                    source_section_title=section.title,
                )
            )

    if section.metrics:
        n_slides = math.ceil(len(section.metrics) / MAX_METRICS_PER_SLIDE)
        for _ in range(n_slides):
            planned.append(
                PlannedSlide(
                    slide_type="metric_summary",
                    title=section.title,
                    source_section_title=section.title,
                )
            )

    for image in section.images:
        planned.append(
            PlannedSlide(
                slide_type="image_caption",
                title=image.title or section.title,
                source_section_title=section.title,
            )
        )
