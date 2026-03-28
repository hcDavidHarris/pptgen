"""Aggregate summariser — Phase 10D.5.

Builds :class:`~pptgen.analytics.ArtifactVersionUsageAggregate` records from
persisted ``artifact_usage_snapshot.json`` files.

**Source of truth**: on-disk run snapshots, never in-memory pipeline state.
The summariser is intentionally decoupled from the pipeline so that aggregates
can be rebuilt at any time by replaying the snapshot files.

Public API::

    build_daily_aggregates(records, target_date)  → list[ArtifactVersionUsageAggregate]
    update_daily_aggregates(analytics_dir, target_date)   → None  (reads + writes)
    rebuild_all_aggregates(analytics_dir)                  → None  (full replay)
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .aggregate_models import ArtifactVersionUsageAggregate

_log = logging.getLogger(__name__)

# Relative paths within analytics_dir
_USAGE_RUNS_SUBDIR = Path("governance") / "usage_runs"
_DAILY_SUBDIR = Path("governance") / "aggregates" / "daily"
_LATEST_SUBDIR = Path("governance") / "aggregates" / "latest"
_SNAPSHOT_FILENAME = "artifact_usage_snapshot.json"
_AGGREGATE_FILENAME = "artifact_version_usage.json"
_LATEST_FILENAME = "artifact_version_usage_latest.json"


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------


def build_daily_aggregates(
    records: list[dict[str, Any]],
    target_date: date,
    now_utc: datetime | None = None,
) -> list[ArtifactVersionUsageAggregate]:
    """Build daily aggregates from a flat list of serialised usage records.

    *records* should be the combined contents of all
    ``artifact_usage_snapshot.json`` files for runs whose ``run_ts`` falls on
    *target_date*.  The caller is responsible for pre-filtering to the correct
    date.

    Each record is a plain dict produced by
    :meth:`~pptgen.analytics.ArtifactUsageRecord.to_dict`.

    Counting rules:

    - ``run_count`` — distinct ``run_id`` values that contain at least one
      record for this (type, family, version) key.
    - ``success_count`` / ``failure_count`` — per distinct ``run_id``; a run is
      marked *success* when any record in that run has
      ``used_in_successful_run=True``, similarly for failure.
    - ``explicit_usage_count`` — runs where **any** record had
      ``resolution_source="explicit"``.
    - ``default_usage_count`` — runs where **no** record had
      ``resolution_source="explicit"`` (i.e. ``run_count - explicit_usage_count``).
      These two fields are mutually exclusive and always sum to ``run_count``.
    - ``draft_override_count`` — runs where **any** record had
      ``is_draft_override_usage=True``.
    - ``deprecated_warning_count`` — runs where **any** record had
      ``warning_emitted=True``.

    Output is sorted deterministically by (artifact_type, artifact_family,
    artifact_version) so that identical inputs always produce identical output.

    Args:
        records:     Flat list of serialised :class:`~pptgen.analytics.ArtifactUsageRecord`
                     dicts (already filtered to ``target_date``).
        target_date: The day this aggregate covers.
        now_utc:     Override for ``last_updated_ts``; defaults to UTC now.

    Returns:
        Sorted list of :class:`~pptgen.analytics.ArtifactVersionUsageAggregate`.
    """
    if not records:
        return []

    now = now_utc or datetime.now(timezone.utc)
    window_start = target_date
    window_end = target_date + timedelta(days=1)

    # Aggregate by (artifact_type, artifact_family, artifact_version).
    # Per-run signal tracking: key → {run_id → {success, failure, explicit, draft, warning}}
    # All four signal flags use OR-merge: once True for a run, stays True.
    # resolution_source uses explicit-wins: if any record in the run was explicit,
    # the run is counted as explicit.
    run_signals: dict[tuple, dict[str, dict[str, bool]]] = defaultdict(dict)

    for rec in records:
        key = (
            rec.get("artifact_type", ""),
            rec.get("artifact_family", ""),
            rec.get("artifact_version"),  # may be None
        )
        run_id = rec.get("run_id", "")

        if run_id not in run_signals[key]:
            run_signals[key][run_id] = {
                "success": False,
                "failure": False,
                "explicit": False,
                "draft": False,
                "warning": False,
            }
        sig = run_signals[key][run_id]
        if rec.get("used_in_successful_run"):
            sig["success"] = True
        if rec.get("used_in_failed_run"):
            sig["failure"] = True
        if rec.get("resolution_source") == "explicit":
            sig["explicit"] = True
        if rec.get("is_draft_override_usage"):
            sig["draft"] = True
        if rec.get("warning_emitted"):
            sig["warning"] = True

    results: list[ArtifactVersionUsageAggregate] = []
    for key in sorted(run_signals.keys()):
        artifact_type, artifact_family, artifact_version = key
        run_map = run_signals[key]

        run_count = len(run_map)
        success_count = sum(1 for v in run_map.values() if v["success"])
        failure_count = sum(1 for v in run_map.values() if v["failure"])
        failure_rate = failure_count / run_count if run_count > 0 else 0.0

        explicit_usage_count = sum(1 for v in run_map.values() if v["explicit"])
        default_usage_count = run_count - explicit_usage_count  # mutually exclusive
        draft_override_count = sum(1 for v in run_map.values() if v["draft"])
        deprecated_warning_count = sum(1 for v in run_map.values() if v["warning"])

        results.append(ArtifactVersionUsageAggregate(
            artifact_type=artifact_type,
            artifact_family=artifact_family,
            artifact_version=artifact_version,
            window_start=window_start,
            window_end=window_end,
            bucket_granularity="daily",
            run_count=run_count,
            success_count=success_count,
            failure_count=failure_count,
            failure_rate=round(failure_rate, 6),
            explicit_usage_count=explicit_usage_count,
            default_usage_count=default_usage_count,
            draft_override_count=draft_override_count,
            deprecated_warning_count=deprecated_warning_count,
            last_updated_ts=now,
        ))

    return results


# ---------------------------------------------------------------------------
# Snapshot I/O helpers (non-blocking)
# ---------------------------------------------------------------------------


def _read_snapshots_for_date(
    usage_runs_dir: Path,
    target_date: date,
) -> list[dict[str, Any]]:
    """Read all usage snapshot records for *target_date* from disk.

    Scans every ``artifact_usage_snapshot.json`` file under *usage_runs_dir*,
    reads its records, and includes those whose ``run_ts`` date matches
    *target_date*.

    Corrupt or unreadable files are silently skipped.

    Returns:
        Flat list of serialised :class:`~pptgen.analytics.ArtifactUsageRecord`
        dicts for runs on *target_date*.
    """
    all_records: list[dict[str, Any]] = []
    for snapshot_path in sorted(usage_runs_dir.glob(f"*/{_SNAPSHOT_FILENAME}")):
        try:
            raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if not isinstance(raw, list) or not raw:
                continue
            # Determine the run's date from the first record's run_ts.
            first_ts_str = raw[0].get("run_ts", "")
            if not first_ts_str:
                continue
            rec_date = datetime.fromisoformat(first_ts_str).date()
            if rec_date == target_date:
                all_records.extend(raw)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Aggregates: skipping corrupt snapshot %s: %s", snapshot_path, exc)
    return all_records


def _write_aggregate_json(
    aggregates: list[ArtifactVersionUsageAggregate],
    path: Path,
) -> None:
    """Write *aggregates* as a JSON array to *path* (deterministic ordering)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            [a.to_dict() for a in aggregates],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Public update / rebuild functions
# ---------------------------------------------------------------------------


def update_daily_aggregates(
    analytics_dir: Path,
    target_date: date | None = None,
) -> None:
    """Rebuild the daily aggregate for *target_date* from persisted snapshots.

    Reads all ``governance/usage_runs/*/artifact_usage_snapshot.json`` files
    whose records belong to *target_date* (determined by ``run_ts`` field),
    builds aggregates via :func:`build_daily_aggregates`, and writes:

    - ``governance/aggregates/daily/<YYYY-MM-DD>/artifact_version_usage.json``
    - ``governance/aggregates/latest/artifact_version_usage_latest.json``

    *target_date* defaults to today (UTC).

    This function is **non-blocking** for the caller: all errors are caught
    and logged at WARNING level.

    Args:
        analytics_dir: Root analytics directory.
        target_date:   The day to aggregate.  Defaults to today UTC.
    """
    try:
        if target_date is None:
            target_date = datetime.now(timezone.utc).date()

        usage_runs_dir = analytics_dir / _USAGE_RUNS_SUBDIR
        if not usage_runs_dir.exists():
            return

        records = _read_snapshots_for_date(usage_runs_dir, target_date)
        aggregates = build_daily_aggregates(records, target_date)

        # Daily file.
        daily_path = analytics_dir / _DAILY_SUBDIR / target_date.isoformat() / _AGGREGATE_FILENAME
        _write_aggregate_json(aggregates, daily_path)

        # Latest file — always overwritten with the most-recently updated day.
        latest_path = analytics_dir / _LATEST_SUBDIR / _LATEST_FILENAME
        _write_aggregate_json(aggregates, latest_path)

    except Exception as exc:  # noqa: BLE001
        _log.warning("Aggregates: failed to update daily aggregates for %s: %s", target_date, exc)


def rebuild_all_aggregates(analytics_dir: Path) -> None:
    """Rebuild all daily aggregates by replaying every persisted run snapshot.

    Useful for recovery after aggregate file corruption or to backfill history.

    Reads *all* ``governance/usage_runs/*/artifact_usage_snapshot.json`` files,
    groups records by ``run_ts`` date, and writes one daily aggregate file per
    unique date found.  The ``latest`` aggregate is set to the most-recent date.

    All errors are caught and logged at WARNING level.

    Args:
        analytics_dir: Root analytics directory.
    """
    try:
        usage_runs_dir = analytics_dir / _USAGE_RUNS_SUBDIR
        if not usage_runs_dir.exists():
            return

        # Group all records by date.
        records_by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for snapshot_path in sorted(usage_runs_dir.glob(f"*/{_SNAPSHOT_FILENAME}")):
            try:
                raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
                if not isinstance(raw, list) or not raw:
                    continue
                first_ts_str = raw[0].get("run_ts", "")
                if not first_ts_str:
                    continue
                rec_date = datetime.fromisoformat(first_ts_str).date()
                records_by_date[rec_date].extend(raw)
            except Exception as exc:  # noqa: BLE001
                _log.warning(
                    "Aggregates: skipping corrupt snapshot %s: %s", snapshot_path, exc
                )

        if not records_by_date:
            return

        # Write daily aggregates for each date.
        now_utc = datetime.now(timezone.utc)
        latest_date: date | None = None

        for d in sorted(records_by_date.keys()):
            aggregates = build_daily_aggregates(records_by_date[d], d, now_utc=now_utc)
            daily_path = analytics_dir / _DAILY_SUBDIR / d.isoformat() / _AGGREGATE_FILENAME
            _write_aggregate_json(aggregates, daily_path)
            latest_date = d

        # Write latest from the most-recent date.
        if latest_date is not None:
            latest_aggregates = build_daily_aggregates(
                records_by_date[latest_date], latest_date, now_utc=now_utc
            )
            latest_path = analytics_dir / _LATEST_SUBDIR / _LATEST_FILENAME
            _write_aggregate_json(latest_aggregates, latest_path)

    except Exception as exc:  # noqa: BLE001
        _log.warning("Aggregates: failed to rebuild all aggregates: %s", exc)
