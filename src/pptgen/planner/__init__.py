"""pptgen slide planning engine.

Public API::

    from pptgen.planner import plan_slides, SlidePlan, PlannedSlide

    slide_plan = plan_slides(presentation_spec, playbook_id="meeting-notes-to-eos-rocks")
    # slide_plan.slide_count       — total planned slides
    # slide_plan.planned_slide_types — ordered list of slide type strings
    # slide_plan.slides             — per-slide PlannedSlide entries
"""

from .planner import plan_slides
from .slide_plan import PlannedSlide, SlidePlan

__all__ = ["plan_slides", "PlannedSlide", "SlidePlan"]
