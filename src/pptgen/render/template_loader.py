"""Template loader.

Loads a .pptx (or .potx) template file from disk and returns a python-pptx
Presentation object.  The Presentation is used as the base for the rendered
output: the renderer adds slides to it and saves to a new output path.

The template file itself is never overwritten.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.presentation import Presentation as PresentationType

from ..errors import TemplateLoadError


def load_template(template_path: Path) -> PresentationType:
    """Open *template_path* and return a Presentation object.

    The file may be .pptx or .potx; python-pptx handles both.

    Raises:
        TemplateLoadError: if the file does not exist or cannot be opened.
    """
    if not template_path.exists():
        raise TemplateLoadError(
            f"Template file not found: '{template_path}'. "
            f"Run scripts/create_template.py to generate template files."
        )

    try:
        return Presentation(str(template_path))
    except Exception as exc:
        raise TemplateLoadError(
            f"Cannot open template '{template_path}': {exc}"
        ) from exc
