"""Unit tests for pptgen generate --template CLI flag."""

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
# --template flag exists
# ---------------------------------------------------------------------------

class TestTemplateFlagExists:
    def test_template_flag_in_generate_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert "--template" in result.output or "-t" in result.output

    def test_template_flag_short_form_in_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Valid template override
# ---------------------------------------------------------------------------

class TestValidTemplateOverride:
    def test_ops_review_template_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--template", "ops_review_v1"],
        )
        assert result.exit_code == 0, result.output

    def test_architecture_template_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_ARCH_NOTES), "--output", str(out), "--template", "architecture_overview_v1"],
        )
        assert result.exit_code == 0, result.output

    def test_executive_brief_template_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_GENERIC), "--output", str(out), "--template", "executive_brief_v1"],
        )
        assert result.exit_code == 0, result.output

    def test_template_override_creates_pptx(self, tmp_path):
        out = tmp_path / "out.pptx"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--template", "executive_brief_v1"],
        )
        assert out.exists()
        assert out.stat().st_size > 0

    def test_short_flag_works(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "-t", "ops_review_v1"],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()


# ---------------------------------------------------------------------------
# Invalid template override
# ---------------------------------------------------------------------------

class TestInvalidTemplateOverride:
    def test_invalid_template_exits_nonzero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--template", "nonexistent_v99"],
        )
        assert result.exit_code != 0

    def test_invalid_template_error_message(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--template", "bad-id"],
        )
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "not registered" in combined.lower() or "error" in combined.lower()

    def test_invalid_template_error_lists_valid_options(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--template", "bad-id"],
        )
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "ops_review_v1" in combined


# ---------------------------------------------------------------------------
# --debug includes template_id
# ---------------------------------------------------------------------------

class TestDebugIncludesTemplate:
    def test_debug_shows_template_id(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            [
                "generate", str(_MEETING_NOTES),
                "--output", str(out),
                "--template", "ops_review_v1",
                "--debug",
            ],
        )
        assert "template_id" in result.output

    def test_debug_shows_correct_template_value(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            [
                "generate", str(_ARCH_NOTES),
                "--output", str(out),
                "--template", "architecture_overview_v1",
                "--debug",
            ],
        )
        assert "architecture_overview_v1" in result.output

    def test_debug_shows_default_template_when_no_override(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_GENERIC), "--output", str(out), "--debug"],
        )
        assert "template_id" in result.output
        assert "ops_review_v1" in result.output


# ---------------------------------------------------------------------------
# Default behavior without --template still works
# ---------------------------------------------------------------------------

class TestDefaultWithoutTemplateFlag:
    def test_no_template_flag_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out)],
        )
        assert result.exit_code == 0, result.output

    def test_no_template_flag_creates_pptx(self, tmp_path):
        out = tmp_path / "out.pptx"
        runner.invoke(app, ["generate", str(_MEETING_NOTES), "--output", str(out)])
        assert out.exists()

    def test_architecture_default_uses_architecture_template(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_ARCH_NOTES), "--output", str(out), "--debug"],
        )
        assert "architecture_overview_v1" in result.output


# ---------------------------------------------------------------------------
# Regression: Stage 4 generate behavior unchanged
# ---------------------------------------------------------------------------

class TestStage4Regression:
    def test_generate_without_template_still_works(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_GENERIC), "--output", str(out)]
        )
        assert result.exit_code == 0

    def test_missing_file_still_fails(self, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        result = runner.invoke(app, ["generate", str(missing)])
        assert result.exit_code != 0
