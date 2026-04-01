"""Tests for stage_timings and artifact_count persistence in SQLiteRunStore."""
from __future__ import annotations

import pytest

from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteRunStore(db_path=tmp_path / "artifacts.db")
    yield s
    s.close()


class TestStageTimingsPersistence:
    def test_stage_timings_round_trip(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        timings = [{"stage": "planning", "duration_ms": 120.5}, {"stage": "rendering", "duration_ms": 340.0}]
        store.update_status(run.run_id, RunStatus.SUCCEEDED, stage_timings=timings)
        fetched = store.get(run.run_id)
        assert fetched.stage_timings == timings

    def test_artifact_count_round_trip(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, artifact_count=4)
        fetched = store.get(run.run_id)
        assert fetched.artifact_count == 4

    def test_stage_timings_none_by_default(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED)
        fetched = store.get(run.run_id)
        assert fetched.stage_timings is None

    def test_artifact_count_none_by_default(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED)
        fetched = store.get(run.run_id)
        assert fetched.artifact_count is None

    def test_empty_timings_list(self, store):
        run = RunRecord.create(source=RunSource.API_SYNC)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, stage_timings=[])
        fetched = store.get(run.run_id)
        assert fetched.stage_timings == []


class TestSchemaMigration:
    def test_migration_safe_on_fresh_db(self, tmp_path):
        # Migration should run without error on a new database
        store = SQLiteRunStore(db_path=tmp_path / "fresh.db")
        run = RunRecord.create(source=RunSource.CLI)
        store.create(run)
        store.update_status(run.run_id, RunStatus.SUCCEEDED, stage_timings=[{"stage": "x", "duration_ms": 1.0}])
        assert store.get(run.run_id).stage_timings == [{"stage": "x", "duration_ms": 1.0}]
        store.close()

    def test_migration_idempotent(self, tmp_path):
        # Opening the same DB twice should not fail
        db = tmp_path / "artifacts.db"
        s1 = SQLiteRunStore(db_path=db)
        s1.close()
        s2 = SQLiteRunStore(db_path=db)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        s2.create(run)
        s2.update_status(run.run_id, RunStatus.SUCCEEDED, artifact_count=2)
        assert s2.get(run.run_id).artifact_count == 2
        s2.close()


class TestListRuns:
    def test_list_runs_empty(self, store):
        assert store.list_runs() == []

    def test_list_runs_returns_all(self, store):
        for _ in range(3):
            r = RunRecord.create(source=RunSource.API_SYNC)
            store.create(r)
        assert len(store.list_runs()) == 3

    def test_list_runs_ordered_newest_first(self, store):
        import time
        ids = []
        for _ in range(3):
            r = RunRecord.create(source=RunSource.API_SYNC)
            store.create(r)
            ids.append(r.run_id)
            time.sleep(0.01)  # ensure distinct started_at
        result = store.list_runs()
        assert result[0].run_id == ids[-1]  # newest first

    def test_list_runs_filter_by_status(self, store):
        r1 = RunRecord.create(source=RunSource.API_SYNC)
        store.create(r1)
        store.update_status(r1.run_id, RunStatus.SUCCEEDED)
        r2 = RunRecord.create(source=RunSource.API_SYNC)
        store.create(r2)
        store.update_status(r2.run_id, RunStatus.FAILED)

        succeeded = store.list_runs(status="succeeded")
        assert len(succeeded) == 1
        assert succeeded[0].run_id == r1.run_id

    def test_list_runs_filter_by_source(self, store):
        r1 = RunRecord.create(source=RunSource.API_SYNC)
        store.create(r1)
        r2 = RunRecord.create(source=RunSource.CLI)
        store.create(r2)

        cli_runs = store.list_runs(source="cli")
        assert len(cli_runs) == 1
        assert cli_runs[0].run_id == r2.run_id

    def test_list_runs_limit(self, store):
        for _ in range(5):
            r = RunRecord.create(source=RunSource.API_SYNC)
            store.create(r)
        assert len(store.list_runs(limit=3)) == 3

    def test_list_runs_offset(self, store):
        ids = []
        for _ in range(4):
            r = RunRecord.create(source=RunSource.API_SYNC)
            store.create(r)
            ids.append(r.run_id)
        all_runs = store.list_runs(limit=4)
        offset_runs = store.list_runs(limit=4, offset=2)
        assert len(offset_runs) == 2
        assert all_runs[2].run_id == offset_runs[0].run_id


class TestListForJob:
    def test_list_for_job_empty(self, store):
        assert store.list_for_job("nonexistent") == []

    def test_list_for_job_returns_matching(self, store):
        r1 = RunRecord.create(source=RunSource.API_ASYNC, job_id="job1")
        r2 = RunRecord.create(source=RunSource.API_ASYNC, job_id="job1")
        r3 = RunRecord.create(source=RunSource.API_ASYNC, job_id="job2")
        store.create(r1)
        store.create(r2)
        store.create(r3)

        job1_runs = store.list_for_job("job1")
        assert len(job1_runs) == 2
        assert all(r.job_id == "job1" for r in job1_runs)

    def test_list_for_job_no_cross_contamination(self, store):
        r = RunRecord.create(source=RunSource.API_ASYNC, job_id="jobA")
        store.create(r)
        assert store.list_for_job("jobB") == []
