"""Tests for Phase 10D.5 — Aggregate Foundations.

Covers:
- build_daily_aggregates: correctness, counting rules, determinism
- update_daily_aggregates: reads from persisted snapshots, writes correct paths
- rebuild_all_aggregates: groups by date, writes all daily + latest
- ArtifactVersionUsageAggregate: to_dict / from_dict round-trip
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from pptgen.analytics import (
    ArtifactVersionUsageAggregate,
    build_daily_aggregates,
    rebuild_all_aggregates,
    update_daily_aggregates,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_TODAY = date(2026, 3, 27)
_NOW_UTC = datetime(2026, 3, 27, 10, 0, 0, tzinfo=timezone.utc)


def _rec(
    *,
    run_id: str = "run-1",
    run_ts: str = "2026-03-27T09:00:00+00:00",
    artifact_type: str = "primitive",
    artifact_family: str = "fc",
    artifact_version: str | None = "1.0.0",
    lifecycle_state: str | None = "approved",
    resolution_source: str = "explicit",
    usage_scope: str = "top_level",
    warning_emitted: bool = False,
    is_draft_override_usage: bool = False,
    used_in_successful_run: bool = True,
    used_in_failed_run: bool = False,
) -> dict:
    return {
        "run_id": run_id,
        "run_ts": run_ts,
        "artifact_type": artifact_type,
        "artifact_family": artifact_family,
        "artifact_version": artifact_version,
        "lifecycle_state": lifecycle_state,
        "resolution_source": resolution_source,
        "usage_scope": usage_scope,
        "warning_emitted": warning_emitted,
        "is_draft_override_usage": is_draft_override_usage,
        "used_in_successful_run": used_in_successful_run,
        "used_in_failed_run": used_in_failed_run,
    }


def _write_snapshot(analytics_dir: Path, run_id: str, records: list[dict]) -> None:
    """Write an artifact_usage_snapshot.json for testing update_daily_aggregates."""
    snap_dir = analytics_dir / "governance" / "usage_runs" / run_id
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / "artifact_usage_snapshot.json").write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# ArtifactVersionUsageAggregate — to_dict / from_dict
# ---------------------------------------------------------------------------

class TestAggregateModelRoundTrip:
    def _make(self) -> ArtifactVersionUsageAggregate:
        return ArtifactVersionUsageAggregate(
            artifact_type="primitive",
            artifact_family="fc",
            artifact_version="1.0.0",
            window_start=_TODAY,
            window_end=_TODAY + timedelta(days=1),
            bucket_granularity="daily",
            run_count=5,
            success_count=4,
            failure_count=1,
            failure_rate=0.2,
            explicit_usage_count=4,
            default_usage_count=1,
            draft_override_count=0,
            deprecated_warning_count=1,
            last_updated_ts=_NOW_UTC,
        )

    def test_to_dict_has_all_fields(self):
        d = self._make().to_dict()
        assert d["artifact_type"] == "primitive"
        assert d["artifact_family"] == "fc"
        assert d["artifact_version"] == "1.0.0"
        assert d["window_start"] == "2026-03-27"
        assert d["window_end"] == "2026-03-28"
        assert d["bucket_granularity"] == "daily"
        assert d["run_count"] == 5
        assert d["success_count"] == 4
        assert d["failure_count"] == 1
        assert d["failure_rate"] == 0.2
        assert d["explicit_usage_count"] == 4
        assert d["default_usage_count"] == 1
        assert d["draft_override_count"] == 0
        assert d["deprecated_warning_count"] == 1
        assert "last_updated_ts" in d

    def test_dates_are_iso_strings(self):
        d = self._make().to_dict()
        assert isinstance(d["window_start"], str)
        assert isinstance(d["window_end"], str)
        date.fromisoformat(d["window_start"])
        date.fromisoformat(d["window_end"])

    def test_from_dict_roundtrip(self):
        original = self._make()
        restored = ArtifactVersionUsageAggregate.from_dict(original.to_dict())
        assert restored.artifact_type == original.artifact_type
        assert restored.run_count == original.run_count
        assert restored.failure_rate == original.failure_rate
        assert restored.window_start == original.window_start

    def test_none_version_serialises(self):
        agg = ArtifactVersionUsageAggregate(
            artifact_type="theme", artifact_family="exec",
            artifact_version=None,
            window_start=_TODAY, window_end=_TODAY + timedelta(days=1),
            bucket_granularity="daily",
            run_count=1, success_count=1, failure_count=0,
            failure_rate=0.0, explicit_usage_count=0, default_usage_count=1,
            draft_override_count=0, deprecated_warning_count=0,
            last_updated_ts=_NOW_UTC,
        )
        d = agg.to_dict()
        assert d["artifact_version"] is None
        restored = ArtifactVersionUsageAggregate.from_dict(d)
        assert restored.artifact_version is None


# ---------------------------------------------------------------------------
# build_daily_aggregates — unit
# ---------------------------------------------------------------------------

class TestBuildDailyAggregates:
    def test_empty_records_returns_empty(self):
        result = build_daily_aggregates([], _TODAY, now_utc=_NOW_UTC)
        assert result == []

    def test_single_success_record(self):
        records = [_rec(used_in_successful_run=True, used_in_failed_run=False)]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        assert len(aggs) == 1
        a = aggs[0]
        assert a.run_count == 1
        assert a.success_count == 1
        assert a.failure_count == 0
        assert a.failure_rate == 0.0

    def test_single_failure_record(self):
        records = [_rec(used_in_successful_run=False, used_in_failed_run=True)]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        a = aggs[0]
        assert a.run_count == 1
        assert a.success_count == 0
        assert a.failure_count == 1
        assert a.failure_rate == 1.0

    def test_two_runs_same_artifact(self):
        records = [
            _rec(run_id="r1", used_in_successful_run=True),
            _rec(run_id="r2", used_in_successful_run=False, used_in_failed_run=True),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        a = aggs[0]
        assert a.run_count == 2
        assert a.success_count == 1
        assert a.failure_count == 1
        assert a.failure_rate == 0.5

    def test_explicit_vs_default_counts(self):
        records = [
            _rec(run_id="r1", resolution_source="explicit"),
            _rec(run_id="r2", resolution_source="default"),
            _rec(run_id="r3", resolution_source="explicit"),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        a = aggs[0]
        assert a.explicit_usage_count == 2
        assert a.default_usage_count == 1

    def test_draft_override_count(self):
        records = [
            _rec(run_id="r1", is_draft_override_usage=True),
            _rec(run_id="r2", is_draft_override_usage=False),
            _rec(run_id="r3", is_draft_override_usage=True),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        assert aggs[0].draft_override_count == 2

    def test_deprecated_warning_count(self):
        records = [
            _rec(run_id="r1", warning_emitted=True),
            _rec(run_id="r2", warning_emitted=True),
            _rec(run_id="r3", warning_emitted=False),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        assert aggs[0].deprecated_warning_count == 2

    def test_two_different_artifact_types(self):
        records = [
            _rec(run_id="r1", artifact_type="primitive", artifact_family="fc"),
            _rec(run_id="r1", artifact_type="layout", artifact_family="two_col"),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        assert len(aggs) == 2
        types = {a.artifact_type for a in aggs}
        assert types == {"primitive", "layout"}

    def test_per_run_success_not_double_counted(self):
        """Two records from same run for same artifact count as ONE run."""
        records = [
            _rec(run_id="r1", usage_scope="top_level", used_in_successful_run=True),
            _rec(run_id="r1", usage_scope="per_slide", used_in_successful_run=True),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        # Both records have same (type, family, version), so both land in same key.
        a = aggs[0]
        assert a.run_count == 1   # one distinct run_id
        assert a.success_count == 1

    def test_deterministic_ordering_by_type_family_version(self):
        records = [
            _rec(artifact_type="theme",     artifact_family="z_last"),
            _rec(artifact_type="primitive", artifact_family="a_first"),
            _rec(artifact_type="layout",    artifact_family="m_mid"),
        ]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        types = [a.artifact_type for a in aggs]
        assert types == sorted(types)

    def test_identical_input_produces_identical_output(self):
        records = [
            _rec(run_id="r1", warning_emitted=True),
            _rec(run_id="r2", is_draft_override_usage=True),
        ]
        out1 = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        out2 = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        assert [a.to_dict() for a in out1] == [a.to_dict() for a in out2]

    def test_failure_rate_zero_when_no_failures(self):
        records = [_rec(used_in_successful_run=True, used_in_failed_run=False)]
        aggs = build_daily_aggregates(records, _TODAY, now_utc=_NOW_UTC)
        assert aggs[0].failure_rate == 0.0

    def test_window_start_and_end_correct(self):
        aggs = build_daily_aggregates([_rec()], _TODAY, now_utc=_NOW_UTC)
        a = aggs[0]
        assert a.window_start == _TODAY
        assert a.window_end == _TODAY + timedelta(days=1)

    def test_bucket_granularity_daily(self):
        aggs = build_daily_aggregates([_rec()], _TODAY, now_utc=_NOW_UTC)
        assert aggs[0].bucket_granularity == "daily"


# ---------------------------------------------------------------------------
# update_daily_aggregates — reads from persisted snapshots
# ---------------------------------------------------------------------------

class TestUpdateDailyAggregates:
    def test_writes_daily_aggregate_file(self, tmp_path: Path):
        records = [_rec(run_id="r1")]
        _write_snapshot(tmp_path, "r1", records)
        update_daily_aggregates(tmp_path, _TODAY)
        out = tmp_path / "governance" / "aggregates" / "daily" / "2026-03-27" / "artifact_version_usage.json"
        assert out.exists()

    def test_writes_latest_aggregate_file(self, tmp_path: Path):
        _write_snapshot(tmp_path, "r1", [_rec()])
        update_daily_aggregates(tmp_path, _TODAY)
        latest = tmp_path / "governance" / "aggregates" / "latest" / "artifact_version_usage_latest.json"
        assert latest.exists()

    def test_content_matches_in_memory_build(self, tmp_path: Path):
        records = [_rec(run_id="r1"), _rec(run_id="r2", used_in_failed_run=True, used_in_successful_run=False)]
        _write_snapshot(tmp_path, "r1", [records[0]])
        _write_snapshot(tmp_path, "r2", [records[1]])
        update_daily_aggregates(tmp_path, _TODAY)

        out_path = tmp_path / "governance" / "aggregates" / "daily" / "2026-03-27" / "artifact_version_usage.json"
        data = json.loads(out_path.read_text())
        assert len(data) == 1
        assert data[0]["run_count"] == 2
        assert data[0]["success_count"] == 1
        assert data[0]["failure_count"] == 1

    def test_only_target_date_snapshots_included(self, tmp_path: Path):
        today_rec = _rec(run_id="today", run_ts="2026-03-27T09:00:00+00:00")
        yesterday_rec = _rec(run_id="yest", run_ts="2026-03-26T09:00:00+00:00",
                              artifact_family="other_fc")
        _write_snapshot(tmp_path, "today", [today_rec])
        _write_snapshot(tmp_path, "yest",  [yesterday_rec])
        update_daily_aggregates(tmp_path, _TODAY)

        out_path = tmp_path / "governance" / "aggregates" / "daily" / "2026-03-27" / "artifact_version_usage.json"
        data = json.loads(out_path.read_text())
        # Only today's record should be in the 2026-03-27 aggregate.
        families = [d["artifact_family"] for d in data]
        assert "fc" in families
        assert "other_fc" not in families

    def test_noop_when_usage_runs_dir_missing(self, tmp_path: Path):
        """Must not raise when the usage_runs dir does not exist."""
        update_daily_aggregates(tmp_path, _TODAY)  # no error

    def test_empty_snapshot_skipped_gracefully(self, tmp_path: Path):
        # Write an empty snapshot file.
        snap_dir = tmp_path / "governance" / "usage_runs" / "empty-run"
        snap_dir.mkdir(parents=True, exist_ok=True)
        (snap_dir / "artifact_usage_snapshot.json").write_text("[]")
        update_daily_aggregates(tmp_path, _TODAY)  # must not raise

    def test_corrupt_snapshot_skipped_gracefully(self, tmp_path: Path):
        snap_dir = tmp_path / "governance" / "usage_runs" / "bad-run"
        snap_dir.mkdir(parents=True, exist_ok=True)
        (snap_dir / "artifact_usage_snapshot.json").write_text("{not valid json")
        update_daily_aggregates(tmp_path, _TODAY)  # must not raise

    def test_aggregate_is_derived_from_files_not_memory(self, tmp_path: Path):
        """Aggregate must not know about in-memory state — only reads files."""
        records = [_rec(run_id="persisted")]
        _write_snapshot(tmp_path, "persisted", records)
        # Do NOT pass any in-memory records — update reads from disk only.
        update_daily_aggregates(tmp_path, _TODAY)
        out = tmp_path / "governance" / "aggregates" / "daily" / "2026-03-27" / "artifact_version_usage.json"
        data = json.loads(out.read_text())
        assert data[0]["run_count"] == 1


# ---------------------------------------------------------------------------
# rebuild_all_aggregates — full replay
# ---------------------------------------------------------------------------

class TestRebuildAllAggregates:
    def test_rebuilds_multiple_dates(self, tmp_path: Path):
        _write_snapshot(tmp_path, "r1", [_rec(run_ts="2026-03-25T09:00:00+00:00")])
        _write_snapshot(tmp_path, "r2", [_rec(run_ts="2026-03-26T09:00:00+00:00")])
        _write_snapshot(tmp_path, "r3", [_rec(run_ts="2026-03-27T09:00:00+00:00")])
        rebuild_all_aggregates(tmp_path)
        for day in ("2026-03-25", "2026-03-26", "2026-03-27"):
            out = tmp_path / "governance" / "aggregates" / "daily" / day / "artifact_version_usage.json"
            assert out.exists(), f"missing daily aggregate for {day}"

    def test_latest_points_to_most_recent_date(self, tmp_path: Path):
        _write_snapshot(tmp_path, "old", [_rec(run_ts="2026-03-25T09:00:00+00:00",
                                               artifact_family="old_fc")])
        _write_snapshot(tmp_path, "new", [_rec(run_ts="2026-03-27T09:00:00+00:00",
                                               artifact_family="new_fc")])
        rebuild_all_aggregates(tmp_path)
        latest = tmp_path / "governance" / "aggregates" / "latest" / "artifact_version_usage_latest.json"
        data = json.loads(latest.read_text())
        families = [d["artifact_family"] for d in data]
        # Latest should reflect the most recent date (2026-03-27)
        assert "new_fc" in families
        assert "old_fc" not in families

    def test_noop_when_no_snapshots(self, tmp_path: Path):
        rebuild_all_aggregates(tmp_path)  # must not raise

    def test_noop_when_usage_runs_missing(self, tmp_path: Path):
        rebuild_all_aggregates(tmp_path)  # must not raise

    def test_deterministic_on_replay(self, tmp_path: Path):
        for i in range(3):
            _write_snapshot(tmp_path, f"r{i}", [_rec(run_id=f"r{i}")])
        rebuild_all_aggregates(tmp_path)
        out = tmp_path / "governance" / "aggregates" / "daily" / "2026-03-27" / "artifact_version_usage.json"
        first = out.read_text()
        rebuild_all_aggregates(tmp_path)
        # run_count stays the same — each run_id is deduplicated per-run.
        second = out.read_text()
        data = json.loads(second)
        assert data[0]["run_count"] == 3


# ---------------------------------------------------------------------------
# Contract enforcement tests — run-level aggregate semantics
# ---------------------------------------------------------------------------


class TestContractEnforcement:
    """Enforce the run-level counting contract for all four signal metrics.

    Key invariants:
    - All four counts (explicit, default, draft, warning) are per distinct run_id.
    - Multiple records from the same run MUST NOT inflate any count beyond 1.
    - explicit_usage_count + default_usage_count == run_count (mutually exclusive).
    - No count exceeds run_count.
    """

    # --- Multi-record-per-run collapse ---

    def test_multiple_records_same_run_explicit_count_once(self):
        """Two explicit records from the same run → explicit_usage_count=1."""
        recs = [
            _rec(run_id="r1", usage_scope="top_level", resolution_source="explicit"),
            _rec(run_id="r1", usage_scope="per_slide", resolution_source="explicit"),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.explicit_usage_count == 1
        assert agg.run_count == 1

    def test_multiple_records_same_run_draft_count_once(self):
        """Two draft-override records from the same run → draft_override_count=1."""
        recs = [
            _rec(run_id="r1", usage_scope="top_level", is_draft_override_usage=True),
            _rec(run_id="r1", usage_scope="per_slide", is_draft_override_usage=True),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.draft_override_count == 1
        assert agg.run_count == 1

    def test_multiple_records_same_run_warning_count_once(self):
        """Two warning-emitted records from the same run → deprecated_warning_count=1."""
        recs = [
            _rec(run_id="r1", usage_scope="top_level", warning_emitted=True),
            _rec(run_id="r1", usage_scope="per_slide", warning_emitted=True),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.deprecated_warning_count == 1
        assert agg.run_count == 1

    # --- Explicit wins over default within a run ---

    def test_explicit_wins_over_default_within_run(self):
        """One explicit + one default record in r1 → r1 counts as explicit."""
        recs = [
            _rec(run_id="r1", usage_scope="top_level", resolution_source="explicit"),
            _rec(run_id="r1", usage_scope="dependency", resolution_source="default"),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.explicit_usage_count == 1
        assert agg.default_usage_count == 0
        assert agg.run_count == 1

    def test_default_only_run_counts_as_default(self):
        """Two default records in r1 → r1 counts as default, not explicit."""
        recs = [
            _rec(run_id="r1", usage_scope="top_level", resolution_source="default"),
            _rec(run_id="r1", usage_scope="per_slide", resolution_source="default"),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.explicit_usage_count == 0
        assert agg.default_usage_count == 1
        assert agg.run_count == 1

    # --- Mutual exclusivity ---

    def test_explicit_default_mutually_exclusive_sum_to_run_count_single_run(self):
        recs = [_rec(run_id="r1")]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.explicit_usage_count + agg.default_usage_count == agg.run_count

    def test_explicit_default_mutually_exclusive_sum_to_run_count_multi_run(self):
        recs = [
            _rec(run_id="r1", resolution_source="explicit"),
            _rec(run_id="r2", resolution_source="default"),
            _rec(run_id="r3", resolution_source="explicit"),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.run_count == 3
        assert agg.explicit_usage_count + agg.default_usage_count == 3
        assert agg.explicit_usage_count == 2
        assert agg.default_usage_count == 1

    # --- No count exceeds run_count ---

    def test_all_counts_lte_run_count_single_run(self):
        recs = [
            _rec(
                run_id="r1",
                usage_scope="top_level",
                resolution_source="explicit",
                is_draft_override_usage=True,
                warning_emitted=True,
            ),
            _rec(
                run_id="r1",
                usage_scope="per_slide",
                resolution_source="explicit",
                is_draft_override_usage=True,
                warning_emitted=True,
            ),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.explicit_usage_count <= agg.run_count
        assert agg.default_usage_count <= agg.run_count
        assert agg.draft_override_count <= agg.run_count
        assert agg.deprecated_warning_count <= agg.run_count

    def test_all_counts_lte_run_count_multi_run(self):
        """With 3 runs each producing 2 records, no count should exceed 3."""
        recs = []
        for i in range(3):
            recs += [
                _rec(run_id=f"r{i}", usage_scope="top_level",
                     resolution_source="explicit", is_draft_override_usage=True,
                     warning_emitted=True),
                _rec(run_id=f"r{i}", usage_scope="per_slide",
                     resolution_source="explicit", is_draft_override_usage=True,
                     warning_emitted=True),
            ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.run_count == 3
        assert agg.explicit_usage_count <= 3
        assert agg.default_usage_count <= 3
        assert agg.draft_override_count <= 3
        assert agg.deprecated_warning_count <= 3

    # --- Mixed signal collapse ---

    def test_mixed_run_signals_collapse_correctly(self):
        """r1: explicit+draft+warning; r2: default only; r3: explicit+warning."""
        recs = [
            _rec(run_id="r1", usage_scope="top_level", resolution_source="explicit",
                 is_draft_override_usage=True, warning_emitted=True),
            _rec(run_id="r1", usage_scope="per_slide", resolution_source="explicit"),
            _rec(run_id="r2", resolution_source="default"),
            _rec(run_id="r3", resolution_source="explicit", warning_emitted=True),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.run_count == 3
        assert agg.explicit_usage_count == 2   # r1, r3
        assert agg.default_usage_count == 1    # r2
        assert agg.draft_override_count == 1   # r1 only
        assert agg.deprecated_warning_count == 2  # r1, r3

    def test_no_draft_signal_means_zero_draft_count(self):
        recs = [
            _rec(run_id="r1", is_draft_override_usage=False),
            _rec(run_id="r2", is_draft_override_usage=False),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.draft_override_count == 0

    def test_no_warning_signal_means_zero_warning_count(self):
        recs = [
            _rec(run_id="r1", warning_emitted=False),
            _rec(run_id="r2", warning_emitted=False),
        ]
        agg = build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)[0]
        assert agg.deprecated_warning_count == 0

    # --- Determinism ---

    def test_deterministic_output_with_multi_record_runs(self):
        """Repeated calls with identical inputs produce identical JSON."""
        recs = []
        for i in range(4):
            recs += [
                _rec(run_id=f"r{i}", usage_scope="top_level",
                     resolution_source="explicit" if i % 2 == 0 else "default",
                     warning_emitted=bool(i % 3 == 0)),
                _rec(run_id=f"r{i}", usage_scope="per_slide",
                     resolution_source="explicit" if i % 2 == 0 else "default"),
            ]
        result_a = [a.to_dict() for a in build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)]
        result_b = [a.to_dict() for a in build_daily_aggregates(recs, _TODAY, now_utc=_NOW_UTC)]
        assert result_a == result_b

    def test_ordering_invariant_across_record_insertion_order(self):
        """Output order must be (type, family, version) regardless of record order."""
        recs_forward = [
            _rec(run_id="r1", artifact_family="aaa"),
            _rec(run_id="r2", artifact_family="zzz"),
        ]
        recs_reversed = [
            _rec(run_id="r2", artifact_family="zzz"),
            _rec(run_id="r1", artifact_family="aaa"),
        ]
        out_f = [a.artifact_family for a in build_daily_aggregates(recs_forward, _TODAY, now_utc=_NOW_UTC)]
        out_r = [a.artifact_family for a in build_daily_aggregates(recs_reversed, _TODAY, now_utc=_NOW_UTC)]
        assert out_f == out_r == ["aaa", "zzz"]
