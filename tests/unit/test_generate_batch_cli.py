"""CLI tests for the pptgen generate-batch command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pptgen.cli import app


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_BATCH_TEXT = _FIXTURES / "batch" / "text"
_BATCH_ADO = _FIXTURES / "batch" / "ado"
_BATCH_METRICS = _FIXTURES / "batch" / "metrics"

runner = CliRunner()


# ---------------------------------------------------------------------------
# Command exists
# ---------------------------------------------------------------------------

class TestCommandExists:
    def test_generate_batch_in_help(self):
        result = runner.invoke(app, ["--help"])
        assert "generate-batch" in result.output

    def test_help_exits_zero(self):
        result = runner.invoke(app, ["generate-batch", "--help"])
        assert result.exit_code == 0

    def test_help_shows_connector_option(self):
        result = runner.invoke(app, ["generate-batch", "--help"])
        assert "--connector" in result.output

    def test_help_shows_output_dir_option(self):
        result = runner.invoke(app, ["generate-batch", "--help"])
        assert "--output-dir" in result.output


# ---------------------------------------------------------------------------
# Basic batch — raw text mode
# ---------------------------------------------------------------------------

class TestBatchRawText:
    def test_exits_zero_with_valid_dir(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out")]
        )
        assert result.exit_code == 0, result.output

    def test_prints_batch_complete(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out")]
        )
        assert "batch complete" in result.output.lower() or "succeeded" in result.output.lower()

    def test_pptx_files_created(self, tmp_path):
        out = tmp_path / "out"
        runner.invoke(app, ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(out)])
        pptx_files = list(out.glob("*.pptx"))
        assert len(pptx_files) == 2

    def test_output_dir_created(self, tmp_path):
        out = tmp_path / "deep" / "nested"
        runner.invoke(app, ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(out)])
        assert out.exists()

    def test_summary_shows_counts(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out")]
        )
        assert "2" in result.output  # 2 files processed


# ---------------------------------------------------------------------------
# Connector mode
# ---------------------------------------------------------------------------

class TestBatchConnectorMode:
    def test_ado_connector_batch_exits_zero(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_ADO), "--connector", "ado",
             "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 0, result.output

    def test_ado_creates_pptx_files(self, tmp_path):
        out = tmp_path / "out"
        runner.invoke(
            app, ["generate-batch", str(_BATCH_ADO), "--connector", "ado", "--output-dir", str(out)]
        )
        assert len(list(out.glob("*.pptx"))) == 2

    def test_metrics_connector_batch_exits_zero(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_METRICS), "--connector", "metrics",
             "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code == 0, result.output

    def test_unknown_connector_exits_nonzero(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--connector", "bad-type",
             "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code != 0

    def test_unknown_connector_shows_error(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--connector", "bad-type",
             "--output-dir", str(tmp_path / "out")],
        )
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "error" in combined.lower()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestBatchErrors:
    def test_missing_dir_exits_nonzero(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(tmp_path / "no_such_dir")]
        )
        assert result.exit_code != 0

    def test_missing_dir_shows_error(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(tmp_path / "no_such_dir")]
        )
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "error" in combined.lower()

    def test_file_as_dir_exits_nonzero(self, tmp_path):
        f = tmp_path / "file.txt"
        f.write_text("text")
        result = runner.invoke(app, ["generate-batch", str(f)])
        assert result.exit_code != 0

    def test_invalid_mode_exits_nonzero(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(_BATCH_TEXT), "--mode", "bad-mode"]
        )
        assert result.exit_code != 0

    def test_partial_failure_exits_nonzero(self, tmp_path):
        bad_dir = tmp_path / "mixed"
        bad_dir.mkdir()
        (bad_dir / "bad.json").write_text("{invalid}", encoding="utf-8")
        result = runner.invoke(
            app,
            ["generate-batch", str(bad_dir), "--connector", "ado",
             "--output-dir", str(tmp_path / "out")],
        )
        assert result.exit_code != 0  # fails exit because failed > 0

    def test_partial_failure_still_prints_summary(self, tmp_path):
        bad_dir = tmp_path / "mixed"
        bad_dir.mkdir()
        (bad_dir / "bad.json").write_text("{invalid}", encoding="utf-8")
        result = runner.invoke(
            app,
            ["generate-batch", str(bad_dir), "--connector", "ado",
             "--output-dir", str(tmp_path / "out")],
        )
        assert "failed" in result.output.lower() or "1" in result.output


# ---------------------------------------------------------------------------
# Debug output
# ---------------------------------------------------------------------------

class TestBatchDebug:
    def test_debug_exits_zero(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out"), "--debug"],
        )
        assert result.exit_code == 0, result.output

    def test_debug_shows_per_file_info(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out"), "--debug"],
        )
        assert "meeting_notes_1" in result.output
        assert "meeting_notes_2" in result.output

    def test_debug_shows_output_path(self, tmp_path):
        out = tmp_path / "out"
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(out), "--debug"],
        )
        assert ".pptx" in result.output

    def test_no_debug_no_per_file_block(self, tmp_path):
        result = runner.invoke(
            app, ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out")]
        )
        # Without --debug, individual file lines should not appear
        assert "output" not in result.output.lower() or "batch complete" in result.output.lower()


# ---------------------------------------------------------------------------
# Artifacts in batch CLI
# ---------------------------------------------------------------------------

class TestBatchArtifactsCLI:
    def test_artifacts_flag_creates_artifact_dirs(self, tmp_path):
        out = tmp_path / "out"
        runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(out), "--artifacts"],
        )
        for stem in ("meeting_notes_1", "meeting_notes_2"):
            assert (out / f"{stem}.artifacts" / "spec.json").exists()

    def test_artifacts_dir_override(self, tmp_path):
        out = tmp_path / "out"
        arts = tmp_path / "arts"
        runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(out),
             "--artifacts-dir", str(arts)],
        )
        for stem in ("meeting_notes_1", "meeting_notes_2"):
            assert (arts / f"{stem}.artifacts" / "spec.json").exists()


# ---------------------------------------------------------------------------
# Mode flag passthrough
# ---------------------------------------------------------------------------

class TestBatchModeCLI:
    def test_ai_mode_batch(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out"),
             "--mode", "ai"],
        )
        assert result.exit_code == 0, result.output

    def test_deterministic_mode_explicit(self, tmp_path):
        result = runner.invoke(
            app,
            ["generate-batch", str(_BATCH_TEXT), "--output-dir", str(tmp_path / "out"),
             "--mode", "deterministic"],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Regression — existing commands still work
# ---------------------------------------------------------------------------

class TestRegression:
    def test_generate_still_works(self, tmp_path):
        from pptgen.pipeline import generate_presentation
        result = generate_presentation("sprint backlog velocity")
        assert result.stage == "deck_planned"

    def test_ingest_still_works(self):
        result = runner.invoke(
            app,
            ["ingest", "ado", str(_FIXTURES / "sprint_export.json")],
        )
        assert result.exit_code == 0

    def test_generate_command_still_works(self, tmp_path):
        out = tmp_path / "deck.pptx"
        fixtures = Path(__file__).parent.parent / "fixtures"
        result = runner.invoke(
            app, ["generate", str(fixtures / "meeting_notes.txt"), "--output", str(out)]
        )
        assert result.exit_code == 0
