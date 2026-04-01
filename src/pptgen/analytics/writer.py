"""Analytics writer — Phase 10D.4.

Non-blocking JSONL append and aggregate maintenance for per-run governance
analytics.  All public functions in this module are **fire-and-forget**:
they catch every exception and emit a WARNING log line rather than
propagating — a broken analytics path must never fail a pipeline run.

Storage layout (all files in *analytics_dir*)::

    run_records.jsonl      — one JSON object per line, one RunRecord per run
    usage_events.jsonl     — one JSON object per line, one ArtifactUsageEvent
                             per (run, artifact) pair
    usage_aggregates.json  — mutable aggregate counts keyed by
                             ``{artifact_type}/{artifact_id}/{version}``

``usage_aggregates.json`` is a derived cache of ``usage_events.jsonl``.
The ``generated_from_line_count`` field records how many event lines were
consumed to produce the current aggregate.  When this count falls behind
the actual number of lines in ``usage_events.jsonl``, the aggregates can
be recomputed from scratch by replaying the JSONL.

Public functions::

    write_run_record(run_record, analytics_dir)
    write_usage_events(events, analytics_dir)
    update_aggregates(events, analytics_dir)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .analytics_models import (
    ArtifactUsageEvent,
    ArtifactUsageRecord,
    GovernanceAuditEvent,
    RunFailureAttribution,
    RunRecord,
)

_log = logging.getLogger(__name__)

_RUN_RECORDS_FILE = "run_records.jsonl"
_USAGE_EVENTS_FILE = "usage_events.jsonl"
_AUDIT_EVENTS_FILE = "audit_events.jsonl"
_AGGREGATES_FILE = "usage_aggregates.json"


# ---------------------------------------------------------------------------
# Public writer functions
# ---------------------------------------------------------------------------


def write_run_record(run_record: RunRecord, analytics_dir: Path) -> None:
    """Append *run_record* as a single JSON line to ``run_records.jsonl``.

    The target directory is created if it does not already exist.  Any I/O
    or serialisation error is caught and logged at WARNING level — the
    caller is never affected.

    Args:
        run_record:    The :class:`~.analytics_models.RunRecord` to persist.
        analytics_dir: Directory where analytics files are written.
    """
    try:
        analytics_dir.mkdir(parents=True, exist_ok=True)
        path = analytics_dir / _RUN_RECORDS_FILE
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(run_record.to_dict(), ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        _log.warning("Analytics: failed to write run record %s: %s", run_record.run_id, exc)


def write_audit_events(
    events: list[GovernanceAuditEvent],
    analytics_dir: Path,
) -> None:
    """Append each event in *events* as a JSON line to ``audit_events.jsonl``.

    No-op when *events* is empty.  The target directory is created if
    necessary.  Errors are caught and logged — the caller is unaffected.

    Args:
        events:        :class:`~.analytics_models.GovernanceAuditEvent` list.
        analytics_dir: Directory where analytics files are written.
    """
    if not events:
        return
    try:
        analytics_dir.mkdir(parents=True, exist_ok=True)
        path = analytics_dir / _AUDIT_EVENTS_FILE
        with path.open("a", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        _log.warning("Analytics: failed to write %d audit event(s): %s", len(events), exc)


def write_usage_events(
    events: list[ArtifactUsageEvent],
    analytics_dir: Path,
) -> None:
    """Append each event in *events* as a JSON line to ``usage_events.jsonl``.

    No-op when *events* is empty.  The target directory is created if
    necessary.  Errors are caught and logged — the caller is unaffected.

    Args:
        events:        :class:`~.analytics_models.ArtifactUsageEvent` list.
        analytics_dir: Directory where analytics files are written.
    """
    if not events:
        return
    try:
        analytics_dir.mkdir(parents=True, exist_ok=True)
        path = analytics_dir / _USAGE_EVENTS_FILE
        with path.open("a", encoding="utf-8") as fh:
            for ev in events:
                fh.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        _log.warning("Analytics: failed to write %d usage event(s): %s", len(events), exc)


def update_aggregates(
    events: list[ArtifactUsageEvent],
    analytics_dir: Path,
) -> None:
    """Merge *events* into the running ``usage_aggregates.json``.

    The aggregate file is read, updated in memory, and rewritten atomically
    (write to the same path — not a tmp-then-rename, which would require
    cross-device move support; single-process assumption for Phase 10D).

    Aggregate structure::

        {
          "generated_from_line_count": <int>,
          "aggregates": {
            "<artifact_type>/<artifact_id>/<version>": {
              "artifact_type": str,
              "artifact_id":   str,
              "version":       str | null,
              "total_runs":    int,
              "success_count": int,
              "failure_count": int,
              "default_version_count": int
            },
            ...
          }
        }

    ``generated_from_line_count`` accumulates the total number of
    :class:`~.analytics_models.ArtifactUsageEvent` lines processed so far.
    It is a staleness indicator: when it equals the number of lines in
    ``usage_events.jsonl``, the aggregates are up to date.

    No-op when *events* is empty.  Corrupt existing aggregate files are
    silently reset.  All errors are caught and logged.

    Args:
        events:        :class:`~.analytics_models.ArtifactUsageEvent` list.
        analytics_dir: Directory where analytics files are written.
    """
    if not events:
        return
    try:
        analytics_dir.mkdir(parents=True, exist_ok=True)
        path = analytics_dir / _AGGREGATES_FILE

        # Load existing state
        aggregates: dict[str, dict] = {}
        line_count: int = 0
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                aggregates = data.get("aggregates", {})
                line_count = int(data.get("generated_from_line_count", 0))
            except (json.JSONDecodeError, ValueError, TypeError):
                # Corrupt file — start fresh; JSONL is the source of truth
                _log.warning("Analytics: corrupt aggregates file — resetting.")
                aggregates = {}
                line_count = 0

        # Apply new events
        for ev in events:
            key = f"{ev.artifact_type}/{ev.artifact_id}/{ev.version}"
            if key not in aggregates:
                aggregates[key] = {
                    "artifact_type": ev.artifact_type,
                    "artifact_id": ev.artifact_id,
                    "version": ev.version,
                    "total_runs": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "default_version_count": 0,
                }
            agg = aggregates[key]
            agg["total_runs"] += 1
            if ev.run_succeeded:
                agg["success_count"] += 1
            else:
                agg["failure_count"] += 1
            if ev.was_default:
                agg["default_version_count"] += 1

        line_count += len(events)

        # Write back
        path.write_text(
            json.dumps(
                {"generated_from_line_count": line_count, "aggregates": aggregates},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning("Analytics: failed to update aggregates: %s", exc)


def write_usage_snapshot(
    records: list[ArtifactUsageRecord],
    analytics_dir: Path,
    run_id: str,
) -> None:
    """Write *records* as a JSON array to the per-run usage snapshot file.

    Output path::

        <analytics_dir>/governance/usage_runs/<run_id>/artifact_usage_snapshot.json

    No-op when *records* is empty.  The target directory is created if
    necessary.  All errors are caught and logged — the caller is unaffected.

    Args:
        records:       List of finalised :class:`~.analytics_models.ArtifactUsageRecord`.
        analytics_dir: Root analytics directory.
        run_id:        UUID of the pipeline run (used in path construction).
    """
    if not records:
        return
    try:
        out_dir = analytics_dir / "governance" / "usage_runs" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "artifact_usage_snapshot.json"
        payload = [r.to_dict() for r in records]
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "Analytics: failed to write usage snapshot for run %s: %s", run_id, exc
        )


def write_failure_attribution(
    attribution: RunFailureAttribution,
    analytics_dir: Path,
    run_id: str,
) -> None:
    """Write *attribution* as a JSON object to the per-run attribution file.

    Output path::

        <analytics_dir>/governance/usage_runs/<run_id>/failure_attribution.json

    The target directory is created if necessary.  All errors are caught and
    logged — the caller is unaffected.

    Args:
        attribution:   The :class:`~.analytics_models.RunFailureAttribution` to persist.
        analytics_dir: Root analytics directory.
        run_id:        UUID of the pipeline run (used in path construction).
    """
    try:
        out_dir = analytics_dir / "governance" / "usage_runs" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "failure_attribution.json"
        path.write_text(
            json.dumps(attribution.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001
        _log.warning(
            "Analytics: failed to write failure attribution for run %s: %s", run_id, exc
        )
