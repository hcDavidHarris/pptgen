"""Tests for job domain models."""

import pytest
from pptgen.jobs.models import JobRecord, JobStatus, WorkloadType


class TestJobRecord:
    def test_create_returns_queued_job(self):
        job = JobRecord.create("some input text")
        assert job.status == JobStatus.QUEUED

    def test_create_generates_unique_job_ids(self):
        j1 = JobRecord.create("text")
        j2 = JobRecord.create("text")
        assert j1.job_id != j2.job_id

    def test_create_generates_unique_run_ids(self):
        j1 = JobRecord.create("text")
        j2 = JobRecord.create("text")
        assert j1.run_id != j2.run_id

    def test_interactive_default_workload(self):
        job = JobRecord.create("text")
        assert job.workload_type == WorkloadType.INTERACTIVE
        assert job.priority == 10

    def test_batch_workload_priority(self):
        job = JobRecord.create("text", workload_type=WorkloadType.BATCH)
        assert job.priority == 0

    def test_is_terminal_queued_false(self):
        job = JobRecord.create("text")
        assert job.is_terminal() is False

    def test_is_terminal_succeeded_true(self):
        job = JobRecord.create("text")
        job.status = JobStatus.SUCCEEDED
        assert job.is_terminal() is True

    def test_is_terminal_failed_true(self):
        job = JobRecord.create("text")
        job.status = JobStatus.FAILED
        assert job.is_terminal() is True

    def test_is_terminal_cancelled_true(self):
        job = JobRecord.create("text")
        job.status = JobStatus.CANCELLED
        assert job.is_terminal() is True

    def test_is_terminal_running_false(self):
        job = JobRecord.create("text")
        job.status = JobStatus.RUNNING
        assert job.is_terminal() is False

    def test_create_sets_template_id(self):
        job = JobRecord.create("text", template_id="ops_review_v1")
        assert job.template_id == "ops_review_v1"

    def test_create_default_max_retries(self):
        job = JobRecord.create("text")
        assert job.max_retries == 3
