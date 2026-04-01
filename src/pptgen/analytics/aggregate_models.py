"""Aggregate models — Phase 10D.5.

Deterministic daily usage aggregates derived from persisted run snapshots.

These models are **not** populated live during pipeline execution; they are
computed by the aggregate summariser after run snapshots are persisted to disk.
The source of truth is always the per-run ``artifact_usage_snapshot.json``
files under ``governance/usage_runs/``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from typing import Any


@dataclass(frozen=True)
class ArtifactVersionUsageAggregate:
    """Daily usage aggregate for one (artifact_type, artifact_family, artifact_version) key.

    Aggregated from all :class:`~pptgen.analytics.ArtifactUsageRecord` instances
    found in persisted ``artifact_usage_snapshot.json`` files whose ``run_ts``
    falls within the daily bucket.

    Counts follow these rules:

    - **run_count** — number of distinct ``run_id`` values that used this
      artifact version on this day.
    - **success_count** / **failure_count** — per distinct ``run_id``;
      a run counts as a success if **any** record for that run_id has
      ``used_in_successful_run=True``, similarly for failure.
    - **explicit_usage_count** — runs where **any** record had
      ``resolution_source="explicit"``.
    - **default_usage_count** — runs where **no** record had
      ``resolution_source="explicit"`` (``run_count - explicit_usage_count``).
      These two fields are mutually exclusive and always sum to ``run_count``.
    - **draft_override_count** — runs where **any** record had
      ``is_draft_override_usage=True``.
    - **deprecated_warning_count** — runs where **any** record had
      ``warning_emitted=True``.

    Attributes:
        artifact_type:           Canonical artifact category.
        artifact_family:         Stable artifact identifier.
        artifact_version:        Resolved version, or ``None`` for ungoverned.
        window_start:            First day of the bucket (inclusive).
        window_end:              First day *after* the bucket (exclusive).
        bucket_granularity:      Always ``"daily"`` for this phase.
        run_count:               Distinct runs using this artifact version.
        success_count:           Runs that completed successfully.
        failure_count:           Runs that failed.
        failure_rate:            ``failure_count / run_count``, or 0.0 when
                                 ``run_count`` is zero.
        explicit_usage_count:    Runs where any record had ``resolution_source="explicit"``.
        default_usage_count:     Runs where no record had ``resolution_source="explicit"``
                                 (equals ``run_count - explicit_usage_count``; mutually
                                 exclusive with ``explicit_usage_count``).
        draft_override_count:    Runs where any record had ``is_draft_override_usage=True``.
        deprecated_warning_count: Runs where any record had ``warning_emitted=True``.
        last_updated_ts:         UTC timestamp when this aggregate was built.
    """

    artifact_type: str
    artifact_family: str
    artifact_version: str | None
    window_start: date
    window_end: date
    bucket_granularity: str  # "daily"
    run_count: int
    success_count: int
    failure_count: int
    failure_rate: float
    explicit_usage_count: int
    default_usage_count: int
    draft_override_count: int
    deprecated_warning_count: int
    last_updated_ts: datetime

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for JSON output.

        Date and datetime fields are rendered as ISO 8601 strings.
        """
        return {
            "artifact_type": self.artifact_type,
            "artifact_family": self.artifact_family,
            "artifact_version": self.artifact_version,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "bucket_granularity": self.bucket_granularity,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "failure_rate": self.failure_rate,
            "explicit_usage_count": self.explicit_usage_count,
            "default_usage_count": self.default_usage_count,
            "draft_override_count": self.draft_override_count,
            "deprecated_warning_count": self.deprecated_warning_count,
            "last_updated_ts": self.last_updated_ts.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArtifactVersionUsageAggregate:
        """Reconstruct from a plain dict (e.g. loaded from a JSON file).

        Date fields may be ISO 8601 strings or pre-parsed :class:`~datetime.date`
        objects.  ``last_updated_ts`` may be a string or a
        :class:`~datetime.datetime` object.
        """
        def _parse_date(v: Any) -> date:
            if isinstance(v, date) and not isinstance(v, datetime):
                return v
            return date.fromisoformat(str(v)[:10])

        def _parse_dt(v: Any) -> datetime:
            if isinstance(v, datetime):
                return v
            return datetime.fromisoformat(str(v))

        return cls(
            artifact_type=data["artifact_type"],
            artifact_family=data["artifact_family"],
            artifact_version=data.get("artifact_version"),
            window_start=_parse_date(data["window_start"]),
            window_end=_parse_date(data["window_end"]),
            bucket_granularity=data.get("bucket_granularity", "daily"),
            run_count=int(data["run_count"]),
            success_count=int(data["success_count"]),
            failure_count=int(data["failure_count"]),
            failure_rate=float(data["failure_rate"]),
            explicit_usage_count=int(data["explicit_usage_count"]),
            default_usage_count=int(data["default_usage_count"]),
            draft_override_count=int(data["draft_override_count"]),
            deprecated_warning_count=int(data["deprecated_warning_count"]),
            last_updated_ts=_parse_dt(data["last_updated_ts"]),
        )
