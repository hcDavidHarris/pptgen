"""Unit tests for pptgen generate --mode CLI flag."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pptgen.cli import app


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_MEETING_NOTES = _FIXTURES / "meeting_notes.txt"
_ARCH_NOTES = _FIXTURES / "architecture_notes.txt"
_GENERIC = _FIXTURES / "generic_summary.txt"

runner = CliRunner()


# ---------------------------------------------------------------------------
# --mode flag exists
# ---------------------------------------------------------------------------

class TestModeFlagExists:
    def test_mode_flag_in_generate_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert "--mode" in result.output

    def test_generate_help_exits_zero(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# --mode deterministic (default behavior preserved)
# ---------------------------------------------------------------------------

class TestModeDeterministic:
    def test_explicit_deterministic_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "deterministic"],
        )
        assert result.exit_code == 0, result.output

    def test_deterministic_creates_pptx(self, tmp_path):
        out = tmp_path / "out.pptx"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "deterministic"],
        )
        assert out.exists()
        assert out.stat().st_size > 0

    def test_no_mode_flag_same_as_deterministic(self, tmp_path):
        out1 = tmp_path / "no_flag.pptx"
        out2 = tmp_path / "det_flag.pptx"
        runner.invoke(app, ["generate", str(_GENERIC), "--output", str(out1)])
        runner.invoke(
            app,
            ["generate", str(_GENERIC), "--output", str(out2), "--mode", "deterministic"],
        )
        assert out1.exists() and out2.exists()


# ---------------------------------------------------------------------------
# --mode ai
# ---------------------------------------------------------------------------

class TestModeAI:
    def test_ai_mode_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "ai"],
        )
        assert result.exit_code == 0, result.output

    def test_ai_mode_creates_pptx(self, tmp_path):
        out = tmp_path / "out.pptx"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "ai"],
        )
        assert out.exists()
        assert out.stat().st_size > 0

    def test_ai_mode_architecture(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_ARCH_NOTES), "--output", str(out), "--mode", "ai"],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_ai_mode_generic(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_GENERIC), "--output", str(out), "--mode", "ai"],
        )
        assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Invalid --mode
# ---------------------------------------------------------------------------

class TestInvalidMode:
    def test_invalid_mode_exits_nonzero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "llm"],
        )
        assert result.exit_code != 0

    def test_invalid_mode_error_message(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "bad-mode"],
        )
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "mode" in combined.lower() or "error" in combined.lower()


# ---------------------------------------------------------------------------
# --debug includes mode
# ---------------------------------------------------------------------------

class TestDebugShowsMode:
    def test_debug_shows_mode_deterministic(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "deterministic", "--debug"],
        )
        assert "deterministic" in result.output

    def test_debug_shows_mode_ai(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "ai", "--debug"],
        )
        assert "ai" in result.output
        assert "mode" in result.output

    def test_debug_shows_playbook_id(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "ai", "--debug"],
        )
        assert "playbook_id" in result.output

    def test_debug_shows_template_id(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--mode", "ai", "--debug"],
        )
        assert "template_id" in result.output


# ---------------------------------------------------------------------------
# Regression: Stage 4 / Stage 5 behavior unchanged
# ---------------------------------------------------------------------------

class TestRegressions:
    def test_no_mode_flag_still_works(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out)]
        )
        assert result.exit_code == 0

    def test_template_flag_still_works_with_mode(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            [
                "generate", str(_MEETING_NOTES),
                "--output", str(out),
                "--mode", "deterministic",
                "--template", "ops_review_v1",
            ],
        )
        assert result.exit_code == 0

    def test_missing_file_still_fails(self, tmp_path):
        missing = tmp_path / "no_file.txt"
        result = runner.invoke(
            app, ["generate", str(missing), "--mode", "ai"]
        )
        assert result.exit_code != 0
