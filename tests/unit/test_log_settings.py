"""Tests for log_level and log_json_format settings."""
from __future__ import annotations

import pytest

from pptgen.config.settings import RuntimeSettings, override_settings


class TestLogSettings:
    def test_log_level_default(self):
        s = RuntimeSettings()
        assert s.log_level == "INFO"

    def test_log_json_format_default_false(self):
        s = RuntimeSettings()
        assert s.log_json_format is False

    def test_log_level_override(self):
        s = RuntimeSettings(log_level="DEBUG")
        assert s.log_level == "DEBUG"

    def test_log_json_format_override(self):
        s = RuntimeSettings(log_json_format=True)
        assert s.log_json_format is True

    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_LOG_LEVEL", "WARNING")
        override_settings(None)
        try:
            s = RuntimeSettings.from_env()
            assert s.log_level == "WARNING"
        finally:
            override_settings(None)

    def test_log_json_format_from_env_true(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_LOG_JSON_FORMAT", "true")
        override_settings(None)
        try:
            s = RuntimeSettings.from_env()
            assert s.log_json_format is True
        finally:
            override_settings(None)

    def test_log_json_format_from_env_1(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_LOG_JSON_FORMAT", "1")
        override_settings(None)
        try:
            s = RuntimeSettings.from_env()
            assert s.log_json_format is True
        finally:
            override_settings(None)

    def test_log_json_format_from_env_false(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_LOG_JSON_FORMAT", "false")
        override_settings(None)
        try:
            s = RuntimeSettings.from_env()
            assert s.log_json_format is False
        finally:
            override_settings(None)
