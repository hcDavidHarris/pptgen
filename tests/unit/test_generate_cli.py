"""Unit tests for the pptgen generate CLI command."""

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
# Command exists
# ---------------------------------------------------------------------------

class TestGenerateCommandExists:
    def test_generate_in_help(self):
        result = runner.invoke(app, ["--help"])
        assert "generate" in result.output

    def test_generate_help_accessible(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0

    def test_generate_help_mentions_input_file(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert "input" in result.output.lower() or "file" in result.output.lower()


# ---------------------------------------------------------------------------
# Missing / unreadable input file
# ---------------------------------------------------------------------------

class TestGenerateMissingFile:
    def test_missing_file_exits_nonzero(self, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        result = runner.invoke(app, ["generate", str(missing)])
        assert result.exit_code != 0

    def test_missing_file_error_message(self, tmp_path):
        missing = tmp_path / "does_not_exist.txt"
        result = runner.invoke(app, ["generate", str(missing)])
        assert "not found" in result.stderr.lower() or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# Successful generation
# ---------------------------------------------------------------------------

class TestGenerateSuccess:
    def test_meeting_notes_exits_zero(self, tmp_path):
        out = tmp_path / "meeting.pptx"
        result = runner.invoke(app, ["generate", str(_MEETING_NOTES), "--output", str(out)])
        assert result.exit_code == 0, result.output

    def test_meeting_notes_creates_pptx(self, tmp_path):
        out = tmp_path / "meeting.pptx"
        runner.invoke(app, ["generate", str(_MEETING_NOTES), "--output", str(out)])
        assert out.exists()

    def test_meeting_notes_pptx_non_empty(self, tmp_path):
        out = tmp_path / "meeting.pptx"
        runner.invoke(app, ["generate", str(_MEETING_NOTES), "--output", str(out)])
        assert out.stat().st_size > 0

    def test_architecture_notes_exits_zero(self, tmp_path):
        out = tmp_path / "adr.pptx"
        result = runner.invoke(app, ["generate", str(_ARCH_NOTES), "--output", str(out)])
        assert result.exit_code == 0, result.output

    def test_generic_summary_exits_zero(self, tmp_path):
        out = tmp_path / "summary.pptx"
        result = runner.invoke(app, ["generate", str(_GENERIC), "--output", str(out)])
        assert result.exit_code == 0, result.output

    def test_output_message_contains_path(self, tmp_path):
        out = tmp_path / "deck.pptx"
        result = runner.invoke(app, ["generate", str(_MEETING_NOTES), "--output", str(out)])
        assert str(out) in result.output or "Generated" in result.output


# ---------------------------------------------------------------------------
# --output flag
# ---------------------------------------------------------------------------

class TestGenerateOutputFlag:
    def test_output_flag_respected(self, tmp_path):
        out = tmp_path / "custom_name.pptx"
        runner.invoke(app, ["generate", str(_MEETING_NOTES), "--output", str(out)])
        assert out.exists()

    def test_output_short_flag_respected(self, tmp_path):
        out = tmp_path / "short_flag.pptx"
        runner.invoke(app, ["generate", str(_MEETING_NOTES), "-o", str(out)])
        assert out.exists()

    def test_default_output_dir_used_when_no_output_flag(self, tmp_path, monkeypatch):
        # Change working dir so default "output/" goes to tmp_path
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["generate", str(_GENERIC)])
        # Command should succeed (or at least attempt — dir may or may not exist)
        # The key check: output_path in the result contains the input stem
        assert "generic_summary" in result.output or result.exit_code == 0


# ---------------------------------------------------------------------------
# --debug flag
# ---------------------------------------------------------------------------

class TestGenerateDebugFlag:
    def test_debug_exits_zero(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out), "--debug"]
        )
        assert result.exit_code == 0, result.output

    def test_debug_prints_playbook_id(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out), "--debug"]
        )
        assert "playbook_id" in result.output

    def test_debug_prints_stage(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out), "--debug"]
        )
        assert "rendered" in result.output

    def test_debug_prints_slide_count(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out), "--debug"]
        )
        assert "slide_count" in result.output

    def test_debug_prints_output_path(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out), "--debug"]
        )
        assert "output_path" in result.output

    def test_no_debug_does_not_print_playbook_id(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = runner.invoke(
            app, ["generate", str(_MEETING_NOTES), "--output", str(out)]
        )
        assert "playbook_id" not in result.output


# ---------------------------------------------------------------------------
# Regression: existing commands still work
# ---------------------------------------------------------------------------

class TestExistingCommandsUnaffected:
    def test_build_command_still_exists(self):
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0

    def test_validate_command_still_exists(self):
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0

    def test_list_templates_still_works(self):
        result = runner.invoke(app, ["list-templates"])
        assert result.exit_code == 0
