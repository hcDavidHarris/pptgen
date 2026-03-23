"""Metrics connector.

Normalises a local DORA/DevOps metrics JSON file into pipeline-ready text.

Expected JSON structure
-----------------------
The connector expects a dict with fields such as::

    {
      "team":    "Platform Engineering",
      "period":  "Q1 2026",
      "dora_metrics": {
        "deployment_frequency":   "4 per day",
        "lead_time_for_changes":  "2 hours",
        "change_failure_rate":    "1.8%",
        "mttr":                   "12 minutes"
      },
      "pipeline_health": {
        "ci_pass_rate":              "97.4%",
        "deployment_pipeline":       "green",
        "rollbacks_this_quarter":    1
      },
      "notes": "Optional free-form notes."
    }

All fields are optional; the connector degrades gracefully when any are
absent.  The output text is intentionally rich in DevOps-classification
signals (``DORA``, ``deployment frequency``, ``change failure rate``,
``MTTR``) so that the input router correctly routes to
``devops-metrics-to-scorecard``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base_connector import ConnectorOutput


class MetricsConnector:
    """Normalises a local DORA metrics JSON file for the pptgen pipeline."""

    def normalize(self, path: Path) -> ConnectorOutput:
        """Read the metrics JSON at *path* and return normalised output.

        Args:
            path: Path to the local metrics JSON file.

        Returns:
            :class:`~pptgen.connectors.base_connector.ConnectorOutput` whose
            ``text`` routes to ``devops-metrics-to-scorecard``.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError:        If *path* is not valid JSON.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Metrics file not found: {path}")

        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse metrics JSON '{path}': {exc}") from exc

        return _process(data)


def _process(data: dict[str, Any]) -> ConnectorOutput:
    """Convert parsed metrics data into a ConnectorOutput."""
    parts: list[str] = []

    team = data.get("team", "")
    period = data.get("period", "")

    if team:
        parts.append(f"Team: {team}")
    if period:
        parts.append(f"Period: {period}")

    # DORA metrics block — must include canonical signal terms.
    parts.append("DORA metrics summary:")
    dora: dict[str, Any] = data.get("dora_metrics") or {}

    deployment_frequency = dora.get("deployment_frequency", "")
    lead_time = dora.get("lead_time_for_changes", "")
    change_failure_rate = dora.get("change_failure_rate", "")
    mttr = dora.get("mttr", "")

    if deployment_frequency:
        parts.append(f"  Deployment frequency: {deployment_frequency}")
    if lead_time:
        parts.append(f"  Lead time for changes: {lead_time}")
    if change_failure_rate:
        parts.append(f"  Change failure rate: {change_failure_rate}")
    if mttr:
        parts.append(f"  Mean time to restore (MTTR): {mttr}")

    # Pipeline health.
    health: dict[str, Any] = data.get("pipeline_health") or {}
    if health:
        parts.append("Pipeline health:")
        ci_pass = health.get("ci_pass_rate", "")
        pipeline_status = health.get("deployment_pipeline", "")
        rollbacks = health.get("rollbacks_this_quarter")

        if ci_pass:
            parts.append(f"  CI pass rate: {ci_pass}")
        if pipeline_status:
            parts.append(f"  Deployment pipeline status: {pipeline_status}")
        if rollbacks is not None:
            parts.append(f"  Rollbacks this quarter: {rollbacks}")

    # Free-form notes.
    notes = data.get("notes", "")
    if notes:
        parts.append(f"Notes: {notes}")

    text = "\n".join(parts)

    metadata = {
        "team": team,
        "period": period,
        "deployment_frequency": deployment_frequency,
        "change_failure_rate": change_failure_rate,
        "mttr": mttr,
    }

    return ConnectorOutput(
        text=text,
        metadata={k: v for k, v in metadata.items() if v},
    )
