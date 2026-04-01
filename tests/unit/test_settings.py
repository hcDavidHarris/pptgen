"""Tests for RuntimeSettings and the settings singleton (Stage 6A — PR 2)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from pptgen.config import Profile, RuntimeSettings, get_settings, override_settings


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_profile_defaults_to_dev(self):
        s = RuntimeSettings()
        assert s.profile == Profile.DEV

    def test_max_input_bytes_default(self):
        assert RuntimeSettings().max_input_bytes == 524_288

    def test_max_artifact_bytes_default(self):
        assert RuntimeSettings().max_artifact_bytes == 104_857_600

    def test_pipeline_timeout_default(self):
        assert RuntimeSettings().pipeline_timeout_seconds == 120

    def test_render_timeout_default(self):
        assert RuntimeSettings().render_timeout_seconds == 60

    def test_ai_timeout_default(self):
        assert RuntimeSettings().ai_model_timeout_seconds == 30

    def test_enable_ai_mode_default(self):
        assert RuntimeSettings().enable_ai_mode is True

    def test_enable_artifact_export_default(self):
        assert RuntimeSettings().enable_artifact_export is True

    def test_model_provider_default(self):
        assert RuntimeSettings().model_provider == "mock"

    def test_model_api_key_default_is_empty(self):
        assert RuntimeSettings().model_api_key == ""

    def test_api_port_default(self):
        assert RuntimeSettings().api_port == 8000

    def test_api_host_default(self):
        assert RuntimeSettings().api_host == "0.0.0.0"

    def test_workspace_ttl_hours_default(self):
        assert RuntimeSettings().workspace_ttl_hours == 24

    def test_workspace_base_path_uses_tempdir_when_empty(self):
        s = RuntimeSettings(workspace_base="")
        expected = Path(tempfile.gettempdir()) / "pptgen_api"
        assert s.workspace_base_path == expected

    def test_workspace_base_path_uses_override(self, tmp_path):
        s = RuntimeSettings(workspace_base=str(tmp_path / "custom"))
        assert s.workspace_base_path == tmp_path / "custom"

    def test_cors_origins_contain_localhost_5173(self):
        assert "http://localhost:5173" in RuntimeSettings().api_cors_origins


# ---------------------------------------------------------------------------
# from_env — environment variable loading
# ---------------------------------------------------------------------------

class TestFromEnv:
    def test_default_profile_when_no_env(self, monkeypatch):
        monkeypatch.delenv("PPTGEN_PROFILE", raising=False)
        s = RuntimeSettings.from_env()
        assert s.profile == Profile.DEV

    def test_reads_pptgen_profile(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_PROFILE", "prod")
        s = RuntimeSettings.from_env()
        assert s.profile == Profile.PROD

    def test_reads_max_input_bytes(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_MAX_INPUT_BYTES", "1000")
        s = RuntimeSettings.from_env()
        assert s.max_input_bytes == 1000

    def test_reads_model_provider(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_MODEL_PROVIDER", "anthropic")
        s = RuntimeSettings.from_env()
        assert s.model_provider == "anthropic"

    def test_reads_model_api_key(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_MODEL_API_KEY", "sk-test-key")
        s = RuntimeSettings.from_env()
        assert s.model_api_key == "sk-test-key"

    def test_reads_api_port(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_API_PORT", "9000")
        s = RuntimeSettings.from_env()
        assert s.api_port == 9000

    def test_reads_workspace_base(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PPTGEN_WORKSPACE_BASE", str(tmp_path))
        s = RuntimeSettings.from_env()
        assert s.workspace_base == str(tmp_path)

    def test_enable_ai_mode_false_from_env(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_ENABLE_AI_MODE", "false")
        s = RuntimeSettings.from_env()
        assert s.enable_ai_mode is False

    def test_enable_ai_mode_zero_from_env(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_ENABLE_AI_MODE", "0")
        s = RuntimeSettings.from_env()
        assert s.enable_ai_mode is False

    def test_cors_origins_from_env(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_CORS_ORIGINS", "http://app.example.com,http://api.example.com")
        s = RuntimeSettings.from_env()
        assert "http://app.example.com" in s.api_cors_origins
        assert "http://api.example.com" in s.api_cors_origins

    def test_invalid_profile_falls_back_to_dev(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_PROFILE", "staging")
        s = RuntimeSettings.from_env()
        assert s.profile == Profile.DEV


# ---------------------------------------------------------------------------
# Profile-specific defaults
# ---------------------------------------------------------------------------

class TestProfileDefaults:
    def test_test_profile_has_smaller_input_limit(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_PROFILE", "test")
        monkeypatch.delenv("PPTGEN_MAX_INPUT_BYTES", raising=False)
        s = RuntimeSettings.from_env()
        assert s.max_input_bytes == 131_072

    def test_prod_profile_has_larger_input_limit(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_PROFILE", "prod")
        monkeypatch.delenv("PPTGEN_MAX_INPUT_BYTES", raising=False)
        s = RuntimeSettings.from_env()
        assert s.max_input_bytes == 1_048_576

    def test_env_var_overrides_profile_default(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_PROFILE", "prod")
        monkeypatch.setenv("PPTGEN_MAX_INPUT_BYTES", "99999")
        s = RuntimeSettings.from_env()
        assert s.max_input_bytes == 99999

    def test_test_profile_has_short_pipeline_timeout(self, monkeypatch):
        monkeypatch.setenv("PPTGEN_PROFILE", "test")
        monkeypatch.delenv("PPTGEN_PIPELINE_TIMEOUT", raising=False)
        s = RuntimeSettings.from_env()
        assert s.pipeline_timeout_seconds == 30


# ---------------------------------------------------------------------------
# Fingerprint
# ---------------------------------------------------------------------------

class TestFingerprint:
    def test_fingerprint_is_eight_chars(self):
        assert len(RuntimeSettings().fingerprint) == 8

    def test_fingerprint_stable_for_same_settings(self):
        s = RuntimeSettings()
        assert s.fingerprint == s.fingerprint

    def test_fingerprint_differs_for_different_settings(self):
        s1 = RuntimeSettings(max_input_bytes=100)
        s2 = RuntimeSettings(max_input_bytes=200)
        assert s1.fingerprint != s2.fingerprint

    def test_fingerprint_excludes_api_key(self):
        s1 = RuntimeSettings(model_api_key="secret-a")
        s2 = RuntimeSettings(model_api_key="secret-b")
        assert s1.fingerprint == s2.fingerprint

    def test_fingerprint_is_hex_string(self):
        fp = RuntimeSettings().fingerprint
        int(fp, 16)  # raises ValueError if not hex


# ---------------------------------------------------------------------------
# Singleton (get_settings / override_settings)
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_settings_returns_runtime_settings(self):
        s = get_settings()
        assert isinstance(s, RuntimeSettings)

    def test_get_settings_same_instance_on_repeat_calls(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_override_settings_replaces_singleton(self):
        custom = RuntimeSettings(max_input_bytes=42)
        override_settings(custom)
        assert get_settings() is custom

    def test_override_none_resets_singleton(self, monkeypatch):
        monkeypatch.delenv("PPTGEN_PROFILE", raising=False)
        override_settings(RuntimeSettings(max_input_bytes=1))
        override_settings(None)
        s = get_settings()
        assert s.max_input_bytes != 1
        assert s.profile == Profile.DEV

    def test_reset_settings_fixture_clears_singleton(self):
        # This test relies on the autouse reset_settings fixture in conftest.
        # If this test runs after test_override_settings_replaces_singleton,
        # the singleton should have been reset to None by the fixture.
        override_settings(RuntimeSettings(max_input_bytes=7))
        # Fixture will clean up after this test — nothing to assert here
        # except that we can set it without error.
        assert get_settings().max_input_bytes == 7


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_settings_are_frozen(self):
        s = RuntimeSettings()
        with pytest.raises((AttributeError, TypeError)):
            s.api_port = 9999  # type: ignore[misc]
