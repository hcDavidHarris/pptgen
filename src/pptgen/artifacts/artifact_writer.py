"""Artifact export utilities.

Writes intermediate pipeline artifacts to disk as JSON files so that
pipeline outputs are inspectable, debuggable, and auditable without
re-running the full pipeline.

Three artifacts are produced:

``spec.json``
    The :class:`~pptgen.spec.presentation_spec.PresentationSpec` serialised
    via Pydantic's ``model_dump()``.

``slide_plan.json``
    The :class:`~pptgen.planner.SlidePlan` serialised via
    :func:`dataclasses.asdict`.

``deck_definition.json``
    The deck YAML dict produced by the spec-to-deck translator — written
    as-is since it is already a plain ``dict``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from ..planner.slide_plan import SlidePlan
from ..spec.presentation_spec import PresentationSpec


# Artifact file names — fixed so consumers can rely on them.
_SPEC_FILE = "spec.json"
_SLIDE_PLAN_FILE = "slide_plan.json"
_DECK_DEFINITION_FILE = "deck_definition.json"


def write_artifacts(
    artifacts_dir: Path,
    presentation_spec: PresentationSpec,
    slide_plan: SlidePlan,
    deck_definition: dict[str, Any],
) -> dict[str, Path]:
    """Write pipeline artifacts to *artifacts_dir* as JSON files.

    Creates *artifacts_dir* (and any missing parents) if it does not
    already exist.

    Args:
        artifacts_dir:     Directory to write artifact files into.
        presentation_spec: The :class:`~pptgen.spec.presentation_spec.PresentationSpec`
                           produced by the playbook executor.
        slide_plan:        The :class:`~pptgen.planner.SlidePlan` produced by
                           the slide planner.
        deck_definition:   The deck YAML dict produced by the spec-to-deck
                           translator.

    Returns:
        Mapping of artifact name to absolute :class:`~pathlib.Path` of the
        written file::

            {
                "spec":            Path("…/spec.json"),
                "slide_plan":      Path("…/slide_plan.json"),
                "deck_definition": Path("…/deck_definition.json"),
            }

    Raises:
        OSError: If *artifacts_dir* cannot be created or files cannot be
                 written.
        TypeError: If any artifact object is not serialisable.
    """
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    spec_path = _write_json(artifacts_dir / _SPEC_FILE, presentation_spec.model_dump())
    plan_path = _write_json(artifacts_dir / _SLIDE_PLAN_FILE, dataclasses.asdict(slide_plan))
    deck_path = _write_json(artifacts_dir / _DECK_DEFINITION_FILE, deck_definition)

    return {
        "spec": spec_path,
        "slide_plan": plan_path,
        "deck_definition": deck_path,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: Any) -> Path:
    """Serialise *data* as indented UTF-8 JSON and write to *path*.

    Returns the absolute path of the written file.
    """
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return path.resolve()
