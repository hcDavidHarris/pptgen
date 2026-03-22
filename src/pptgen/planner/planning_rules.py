"""Centralized planning rules for the slide planner.

All thresholds that govern how a PresentationSpec is translated into slides
are defined here.  Downstream modules (planner, spec_to_deck) must treat these
as the authoritative limits; do not re-define them locally.
"""

# Maximum bullet items to render on a single bullets slide.
# Sections with more bullets produce multiple slides.
MAX_BULLETS_PER_SLIDE: int = 6

# Maximum metrics to render on a single metric_summary slide.
# Sections with more metrics produce multiple slides.
MAX_METRICS_PER_SLIDE: int = 4
