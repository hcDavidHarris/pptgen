"""CLI tests for --artifacts and --artifacts-dir flags."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pptgen.cli import app


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_MEETING_NOTES = _FIXTURES / "meeting_notes.txt"
_GENERIC = _FIXTURES / "generic_summary.txt"

runner = CliRunner()


# ---------------------------------------------------------------------------
# --artifacts flag
# ---------------------------------------------------------------------------

class TestArtifactsFlag:
    def test_artifacts_flag_in_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert "--artifacts" in result.output

    def test_artifacts_dir_flag_in_help(self):
        result = runner.invoke(app, ["generate", "--help"])
        assert "--artifacts-dir" in result.output

    def test_artifacts_flag_exits_zero(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts-dir", str(arts)],
        )
        assert result.exit_code == 0, result.output

    def test_artifacts_flag_creates_spec_json(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts-dir", str(arts)],
        )
        assert (arts / "spec.json").exists()

    def test_artifacts_flag_creates_slide_plan_json(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts-dir", str(arts)],
        )
        assert (arts / "slide_plan.json").exists()

    def test_artifacts_flag_creates_deck_definition_json(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts-dir", str(arts)],
        )
        assert (arts / "deck_definition.json").exists()

    def test_artifacts_flag_also_creates_pptx(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts-dir", str(arts)],
        )
        assert out.exists()


# ---------------------------------------------------------------------------
# --artifacts default directory convention
# ---------------------------------------------------------------------------

class TestArtifactsDefaultDir:
    def test_default_artifacts_dir_created(self, tmp_path):
        out = tmp_path / "meeting.pptx"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts"],
        )
        # Default: <output_stem>.artifacts/ next to .pptx
        expected_dir = tmp_path / "meeting.artifacts"
        assert expected_dir.exists()

    def test_default_artifacts_dir_contains_spec(self, tmp_path):
        out = tmp_path / "meeting.pptx"
        runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--artifacts"],
        )
        assert (tmp_path / "meeting.artifacts" / "spec.json").exists()

    def test_artifacts_dir_overrides_default(self, tmp_path):
        out = tmp_path / "meeting.pptx"
        custom = tmp_path / "custom_dir"
        runner.invoke(
            app,
            [
                "generate", str(_MEETING_NOTES),
                "--output", str(out),
                "--artifacts-dir", str(custom),
            ],
        )
        assert custom.exists()
        assert (custom / "spec.json").exists()
        # Default dir should NOT be created
        assert not (tmp_path / "meeting.artifacts").exists()


# ---------------------------------------------------------------------------
# --artifacts with --mode ai
# ---------------------------------------------------------------------------

class TestArtifactsAIMode:
    def test_artifacts_with_ai_mode(self, tmp_path):
        out = tmp_path / "ai.pptx"
        arts = tmp_path / "arts"
        result = runner.invoke(
            app,
            [
                "generate", str(_MEETING_NOTES),
                "--output", str(out),
                "--mode", "ai",
                "--artifacts-dir", str(arts),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (arts / "spec.json").exists()
        assert out.exists()


# ---------------------------------------------------------------------------
# --debug shows artifact summary
# ---------------------------------------------------------------------------

class TestArtifactsDebugOutput:
    def test_debug_shows_artifacts_dir(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        result = runner.invoke(
            app,
            [
                "generate", str(_MEETING_NOTES),
                "--output", str(out),
                "--artifacts-dir", str(arts),
                "--debug",
            ],
        )
        assert "artifacts" in result.output.lower()

    def test_debug_without_artifacts_no_artifact_line(self, tmp_path):
        out = tmp_path / "deck.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out), "--debug"],
        )
        # No artifact directory line when artifacts not requested
        assert "artifacts" not in result.output.lower() or "artifacts-dir" not in result.output


# ---------------------------------------------------------------------------
# Regression: existing behavior unchanged without --artifacts
# ---------------------------------------------------------------------------

class TestRegressionNoArtifacts:
    def test_generate_without_artifacts_still_works(self, tmp_path):
        out = tmp_path / "deck.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_MEETING_NOTES), "--output", str(out)],
        )
        assert result.exit_code == 0, result.output
        assert out.exists()

    def test_no_artifact_files_when_flag_absent(self, tmp_path):
        out = tmp_path / "deck.pptx"
        runner.invoke(app, ["generate", str(_GENERIC), "--output", str(out)])
        # No .json files should appear in tmp_path
        json_files = list(tmp_path.glob("*.json"))
        assert json_files == []

    def test_mode_flag_still_works(self, tmp_path):
        out = tmp_path / "deck.pptx"
        result = runner.invoke(
            app,
            ["generate", str(_GENERIC), "--output", str(out), "--mode", "deterministic"],
        )
        assert result.exit_code == 0
