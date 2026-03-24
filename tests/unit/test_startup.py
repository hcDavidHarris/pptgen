"""Tests for validate_startup and assert_startup_healthy (Stage 6A — PR 4)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pptgen.config import RuntimeSettings
from pptgen.runtime.startup import validate_startup, assert_startup_healthy, _REGISTRY_PATH


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings_with_writable_workspace(tmp_path: Path) -> RuntimeSettings:
    """Return a minimal healthy settings object using tmp_path as workspace."""
    return RuntimeSettings(workspace_base=str(tmp_path))


# ---------------------------------------------------------------------------
# validate_startup — healthy path
# ---------------------------------------------------------------------------

class TestValidateStartupHealthy:
    def test_healthy_returns_empty_list(self, tmp_path):
        settings = _settings_with_writable_workspace(tmp_path)
        failures = validate_startup(settings)
        assert failures == []

    def test_mock_provider_no_api_key_is_healthy(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            model_provider="mock",
            model_api_key="",
        )
        failures = validate_startup(settings)
        assert not any("API_KEY" in f for f in failures)


# ---------------------------------------------------------------------------
# validate_startup — registry checks
# ---------------------------------------------------------------------------

class TestValidateStartupRegistry:
    def test_missing_registry_is_reported(self, tmp_path):
        settings = _settings_with_writable_workspace(tmp_path)
        with patch(
            "pptgen.runtime.startup._REGISTRY_PATH",
            tmp_path / "nonexistent_registry.yaml",
        ):
            failures = validate_startup(settings)
        assert any("registry" in f.lower() for f in failures)

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not supported on Windows")
    def test_unreadable_registry_is_reported(self, tmp_path):
        import os
        registry = tmp_path / "registry.yaml"
        registry.write_text("templates: []", encoding="utf-8")
        os.chmod(registry, 0o000)
        try:
            settings = _settings_with_writable_workspace(tmp_path)
            with patch("pptgen.runtime.startup._REGISTRY_PATH", registry):
                failures = validate_startup(settings)
            assert any("registry" in f.lower() for f in failures)
        finally:
            os.chmod(registry, 0o644)


# ---------------------------------------------------------------------------
# validate_startup — workspace checks
# ---------------------------------------------------------------------------

class TestValidateStartupWorkspace:
    def test_unwritable_workspace_is_reported(self, tmp_path):
        settings = _settings_with_writable_workspace(tmp_path)
        with patch(
            "pptgen.runtime.workspace.WorkspaceManager.is_base_writable",
            return_value=False,
        ):
            failures = validate_startup(settings)
        assert any("writable" in f.lower() or "workspace" in f.lower() for f in failures)


# ---------------------------------------------------------------------------
# validate_startup — AI provider checks
# ---------------------------------------------------------------------------

class TestValidateStartupAIProvider:
    def test_anthropic_provider_without_key_is_reported(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            model_provider="anthropic",
            model_api_key="",
            enable_ai_mode=True,
        )
        failures = validate_startup(settings)
        assert any("API_KEY" in f or "api_key" in f.lower() for f in failures)

    def test_anthropic_provider_with_key_passes(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            model_provider="anthropic",
            model_api_key="sk-test-key",
            enable_ai_mode=True,
        )
        # Only AI check should pass — other checks may or may not pass
        failures = validate_startup(settings)
        assert not any("API_KEY" in f or "api_key" in f.lower() for f in failures)

    def test_ai_mode_disabled_skips_key_check(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            model_provider="anthropic",
            model_api_key="",
            enable_ai_mode=False,
        )
        failures = validate_startup(settings)
        assert not any("API_KEY" in f for f in failures)


# ---------------------------------------------------------------------------
# validate_startup — input size limit checks
# ---------------------------------------------------------------------------

class TestValidateStartupInputSize:
    def test_zero_max_input_bytes_is_reported(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            max_input_bytes=0,
        )
        failures = validate_startup(settings)
        assert any("max_input_bytes" in f for f in failures)

    def test_negative_max_input_bytes_is_reported(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            max_input_bytes=-1,
        )
        failures = validate_startup(settings)
        assert any("max_input_bytes" in f for f in failures)

    def test_positive_max_input_bytes_passes(self, tmp_path):
        settings = _settings_with_writable_workspace(tmp_path)
        failures = validate_startup(settings)
        assert not any("max_input_bytes" in f for f in failures)


# ---------------------------------------------------------------------------
# assert_startup_healthy
# ---------------------------------------------------------------------------

class TestAssertStartupHealthy:
    def test_raises_runtime_error_on_failure(self, tmp_path):
        settings = _settings_with_writable_workspace(tmp_path)
        with patch(
            "pptgen.runtime.startup._REGISTRY_PATH",
            tmp_path / "missing_registry.yaml",
        ):
            with pytest.raises(RuntimeError, match="startup validation failed"):
                assert_startup_healthy(settings)

    def test_error_message_lists_all_failures(self, tmp_path):
        settings = RuntimeSettings(
            workspace_base=str(tmp_path),
            max_input_bytes=0,
            model_provider="anthropic",
            model_api_key="",
            enable_ai_mode=True,
        )
        with patch(
            "pptgen.runtime.startup._REGISTRY_PATH",
            tmp_path / "missing_registry.yaml",
        ):
            with pytest.raises(RuntimeError) as exc_info:
                assert_startup_healthy(settings)
        msg = str(exc_info.value)
        # Multiple failures should all appear in the error message
        assert "registry" in msg.lower()
        assert "max_input_bytes" in msg

    def test_no_exception_when_healthy(self, tmp_path):
        settings = _settings_with_writable_workspace(tmp_path)
        # Should not raise — registry exists in the actual repo
        assert_startup_healthy(settings)
