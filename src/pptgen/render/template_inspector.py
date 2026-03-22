"""Template inspector.

Inspects a loaded Presentation and builds a mapping of layout names to
SlideLayout objects.  The deck renderer uses this mapping to look up the
correct layout for each YAML slide type before adding the slide.

Design note: layout discovery is name-based.  Templates must follow the
naming convention from the Template Authoring Standard:

    Title Layout
    Section Layout
    Bullets Layout
    Two Column Layout
    Metric Summary Layout
    Image Caption Layout
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pptx.presentation import Presentation as PresentationType
from pptx.slide import SlideLayout

from ..errors import TemplateCompatibilityError


@dataclass
class TemplateInspection:
    """Result of inspecting a Presentation's slide master layouts.

    Attributes:
        layout_map: dict mapping layout name → SlideLayout object.
    """

    layout_map: dict[str, SlideLayout] = field(default_factory=dict)

    def get_layout(self, layout_name: str) -> SlideLayout:
        """Return the SlideLayout for *layout_name*.

        Raises:
            TemplateCompatibilityError: if the layout is not present.
        """
        layout = self.layout_map.get(layout_name)
        if layout is None:
            available = sorted(self.layout_map)
            raise TemplateCompatibilityError(
                f"Layout '{layout_name}' not found in template. "
                f"Available layouts: {available}"
            )
        return layout

    def layout_names(self) -> list[str]:
        """Return a sorted list of all layout names in this template."""
        return sorted(self.layout_map)


def inspect_template(presentation: PresentationType) -> TemplateInspection:
    """Inspect *presentation* and return a TemplateInspection.

    Iterates over every slide master and collects all slide layouts by name.
    Duplicate layout names across masters are resolved in favour of the first
    occurrence (slide masters are ordered as stored in the file).
    """
    layout_map: dict[str, SlideLayout] = {}
    for master in presentation.slide_masters:
        for layout in master.slide_layouts:
            if layout.name not in layout_map:
                layout_map[layout.name] = layout
    return TemplateInspection(layout_map=layout_map)
