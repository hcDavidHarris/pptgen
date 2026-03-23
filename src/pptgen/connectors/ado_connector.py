"""ADO (Azure DevOps) connector.

Normalises a local JSON sprint export into pipeline-ready text.

Expected JSON structure
-----------------------
The connector expects a dict with fields such as::

    {
      "sprint":                  "Sprint 12",
      "iteration":               "2026-03-14 to 2026-03-28",
      "team":                    "Platform Engineering",
      "velocity":                38,
      "story_points_committed":  42,
      "story_points_completed":  38,
      "blocked_count":           2,
      "bugs":                    3,
      "pull_requests":           14,
      "work_items": [
        {"id": 1001, "title": "...", "type": "Feature",
         "status": "Completed", "story_points": 8},
        ...
      ],
      "notes": "Optional free-form notes."
    }

All fields are optional; the connector degrades gracefully when any are
absent.  The output text is intentionally rich in ADO-classification
signals (``sprint``, ``backlog``, ``velocity``, ``story points``,
``blocked``, ``work items``) so that the input router correctly routes to
``ado-summary-to-weekly-delivery``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base_connector import ConnectorOutput


class ADOConnector:
    """Normalises a local Azure DevOps sprint export for the pptgen pipeline."""

    def normalize(self, path: Path) -> ConnectorOutput:
        """Read the sprint JSON at *path* and return normalised output.

        Args:
            path: Path to the local ADO sprint export JSON file.

        Returns:
            :class:`~pptgen.connectors.base_connector.ConnectorOutput` whose
            ``text`` routes to ``ado-summary-to-weekly-delivery``.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError:        If *path* is not valid JSON.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"ADO export file not found: {path}")

        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse ADO JSON '{path}': {exc}") from exc

        return _process(data)


def _process(data: dict[str, Any]) -> ConnectorOutput:
    """Convert parsed ADO sprint data into a ConnectorOutput."""
    parts: list[str] = []

    sprint = data.get("sprint", "")
    team = data.get("team", "")
    iteration = data.get("iteration", "")

    if sprint:
        parts.append(f"Sprint: {sprint}")
    if team:
        parts.append(f"Team: {team}")
    if iteration:
        parts.append(f"Iteration: {iteration}")

    # Velocity and story points — key ADO routing signals.
    velocity = data.get("velocity")
    committed = data.get("story_points_committed")
    completed = data.get("story_points_completed")

    if velocity is not None:
        parts.append(f"Velocity: {velocity} story points delivered this sprint.")
    if committed is not None and completed is not None:
        parts.append(
            f"Story points committed: {committed}.  "
            f"Story points completed: {completed}."
        )

    # Blocked items.
    blocked = data.get("blocked_count", 0)
    if blocked:
        parts.append(f"Blocked work items: {blocked} item(s) blocked in backlog.")

    # Bug count.
    bugs = data.get("bugs")
    if bugs:
        parts.append(f"Bugs resolved: {bugs}.")

    # Pull requests.
    prs = data.get("pull_requests")
    if prs:
        parts.append(f"Pull requests merged: {prs}.")

    # Work item details.
    work_items: list[dict[str, Any]] = data.get("work_items") or []
    if work_items:
        parts.append(f"Work items this sprint ({len(work_items)} total):")
        for item in work_items:
            title = item.get("title", "Untitled")
            status = item.get("status", "Unknown")
            points = item.get("story_points", "")
            pts_str = f" ({points} story points)" if points else ""
            parts.append(f"  - {title} [{status}]{pts_str}")

    # Free-form notes.
    notes = data.get("notes", "")
    if notes:
        parts.append(f"Notes: {notes}")

    text = "\n".join(parts)

    metadata = {
        "sprint": sprint,
        "team": team,
        "velocity": velocity,
        "blocked_count": blocked,
        "work_item_count": len(work_items),
    }

    return ConnectorOutput(text=text, metadata={k: v for k, v in metadata.items() if v is not None})
