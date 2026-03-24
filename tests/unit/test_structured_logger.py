"""Tests for structured logging utilities."""
from __future__ import annotations

import json
import logging

import pytest

from pptgen.observability.structured_logger import JsonFormatter, StructuredLogger, get_logger


class TestJsonFormatter:
    def test_format_produces_valid_json(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="hello", args=(), exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "ts" in data
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "hello"

    def test_format_includes_event_field(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="run_completed", args=(), exc_info=None,
        )
        record.event = "run_completed"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["event"] == "run_completed"

    def test_format_includes_run_id(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="e", args=(), exc_info=None,
        )
        record.run_id = "abc123"
        output = formatter.format(record)
        assert json.loads(output)["run_id"] == "abc123"

    def test_format_omits_absent_fields(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="e", args=(), exc_info=None,
        )
        data = json.loads(formatter.format(record))
        assert "run_id" not in data
        assert "job_id" not in data


class TestStructuredLogger:
    def _make_logger(self, name="test.structured"):
        return StructuredLogger(name)

    def test_event_emits_log_record(self, caplog):
        slog = self._make_logger("test.event")
        with caplog.at_level(logging.INFO, logger="test.event"):
            slog.event("test_event", run_id="r1")
        assert any("test_event" in r.message for r in caplog.records)

    def test_event_sets_run_id_extra(self, caplog):
        slog = self._make_logger("test.run_id")
        with caplog.at_level(logging.INFO, logger="test.run_id"):
            slog.event("some_event", run_id="myrunid")
        record = caplog.records[0]
        assert record.run_id == "myrunid"

    def test_run_completed_event_type(self, caplog):
        slog = self._make_logger("test.run_completed")
        with caplog.at_level(logging.INFO, logger="test.run_completed"):
            slog.run_completed("run1", total_ms=500.0)
        assert caplog.records[0].event == "run_completed"

    def test_run_failed_event_type(self, caplog):
        slog = self._make_logger("test.run_failed")
        with caplog.at_level(logging.INFO, logger="test.run_failed"):
            slog.run_failed("run2", error_category="planning")
        assert caplog.records[0].event == "run_failed"

    def test_job_claimed_sets_job_id(self, caplog):
        slog = self._make_logger("test.job_claimed")
        with caplog.at_level(logging.INFO, logger="test.job_claimed"):
            slog.job_claimed("job1", run_id="run1", worker_id="w1")
        record = caplog.records[0]
        assert record.event == "job_claimed"
        assert record.job_id == "job1"

    def test_job_failed_uses_warning_level(self, caplog):
        slog = self._make_logger("test.job_failed")
        with caplog.at_level(logging.WARNING, logger="test.job_failed"):
            slog.job_failed("job1", run_id="run1", error="oops")
        assert caplog.records[0].levelno == logging.WARNING

    def test_artifact_promoted_event_type(self, caplog):
        slog = self._make_logger("test.artifact")
        with caplog.at_level(logging.INFO, logger="test.artifact"):
            slog.artifact_promoted("run1", artifact_type="pptx", size_bytes=1024, checksum="sha256:abc")
        assert caplog.records[0].event == "artifact_promoted"

    def test_get_logger_returns_structured_logger(self):
        logger = get_logger("some.module")
        assert isinstance(logger, StructuredLogger)
