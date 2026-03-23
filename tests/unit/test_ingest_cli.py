"""CLI tests for the pptgen ingest command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pptgen.cli import app


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_TRANSCRIPT = _FIXTURES / "transcript.txt"
_SPRINT = _FIXTURES / "sprint_export.json"
_METRICS = _FIXTURES / "devops_metrics.json"

runner = CliRunner()


# ---------------------------------------------------------------------------
# Command exists and help is accessible
# ---------------------------------------------------------------------------

class TestIngestCommandExists:
    def test_ingest_in_app_help(self):
        result = runner.invoke(app, ["--help"])
        assert "ingest" in result.output

    def test_ingest_help_exits_zero(self):
        result = runner.invoke(app, ["ingest", "--help"])
        assert result.exit_code == 0

    def test_ingest_help_shows_connector_types(self):
        result = runner.invoke(app, ["ingest", "--help"])
        assert "transcript" in result.output or "ado" in result.output


# ---------------------------------------------------------------------------
# Transcript ingest
# ---------------------------------------------------------------------------

class TestIngestTranscript:
    def test_exits_zero(self):
        result = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        assert result.exit_code == 0, result.output

    def test_output_is_non_empty(self):
        result = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        assert result.output.strip()

    def test_output_contains_meeting_signal(self):
        result = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        assert "meeting" in result.output.lower() or "attendees" in result.output.lower()

    def test_output_is_deterministic(self):
        r1 = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        r2 = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        assert r1.output == r2.output


# ---------------------------------------------------------------------------
# ADO ingest
# ---------------------------------------------------------------------------

class TestIngestADO:
    def test_exits_zero(self):
        result = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        assert result.exit_code == 0, result.output

    def test_output_is_non_empty(self):
        result = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        assert result.output.strip()

    def test_output_contains_sprint_signal(self):
        result = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        assert "sprint" in result.output.lower()

    def test_output_contains_velocity(self):
        result = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        assert "velocity" in result.output.lower()

    def test_output_is_deterministic(self):
        r1 = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        r2 = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        assert r1.output == r2.output


# ---------------------------------------------------------------------------
# Metrics ingest
# ---------------------------------------------------------------------------

class TestIngestMetrics:
    def test_exits_zero(self):
        result = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        assert result.exit_code == 0, result.output

    def test_output_is_non_empty(self):
        result = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        assert result.output.strip()

    def test_output_contains_dora_signal(self):
        result = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        assert "dora" in result.output.lower() or "deployment" in result.output.lower()

    def test_output_contains_change_failure_rate(self):
        result = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        assert "change failure rate" in result.output.lower()

    def test_output_is_deterministic(self):
        r1 = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        r2 = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        assert r1.output == r2.output


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestIngestErrors:
    def test_missing_file_exits_nonzero(self):
        result = runner.invoke(app, ["ingest", "transcript", "no_such_file.txt"])
        assert result.exit_code != 0

    def test_missing_file_shows_error(self):
        result = runner.invoke(app, ["ingest", "transcript", "no_such_file.txt"])
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "error" in combined.lower() or "not found" in combined.lower()

    def test_unknown_connector_exits_nonzero(self, tmp_path):
        f = tmp_path / "dummy.txt"
        f.write_text("x")
        result = runner.invoke(app, ["ingest", "bad-connector-type", str(f)])
        assert result.exit_code != 0

    def test_unknown_connector_shows_error(self, tmp_path):
        f = tmp_path / "dummy.txt"
        f.write_text("x")
        result = runner.invoke(app, ["ingest", "bad-connector-type", str(f)])
        combined = result.output + (result.stderr if hasattr(result, "stderr") else "")
        assert "error" in combined.lower() or "unknown" in combined.lower()

    def test_malformed_json_exits_nonzero(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid}", encoding="utf-8")
        result = runner.invoke(app, ["ingest", "ado", str(bad)])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Debug flag
# ---------------------------------------------------------------------------

class TestIngestDebug:
    def test_debug_flag_exits_zero(self):
        result = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT), "--debug"])
        assert result.exit_code == 0, result.output

    def test_debug_output_contains_connector_name(self):
        result = runner.invoke(app, ["ingest", "ado", str(_SPRINT), "--debug"])
        # Debug output goes to stderr; CliRunner mixes streams by default
        assert "ado" in result.output.lower()

    def test_without_debug_no_metadata_header(self):
        result = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        assert "connector" not in result.output.lower()
        assert "metadata" not in result.output.lower()


# ---------------------------------------------------------------------------
# Pipeline compatibility
# ---------------------------------------------------------------------------

class TestIngestPipelineCompatibility:
    def test_transcript_text_routes_correctly(self):
        from pptgen.input_router import route_input
        result = runner.invoke(app, ["ingest", "transcript", str(_TRANSCRIPT)])
        assert route_input(result.output) == "meeting-notes-to-eos-rocks"

    def test_ado_text_routes_correctly(self):
        from pptgen.input_router import route_input
        result = runner.invoke(app, ["ingest", "ado", str(_SPRINT)])
        assert route_input(result.output) == "ado-summary-to-weekly-delivery"

    def test_metrics_text_routes_correctly(self):
        from pptgen.input_router import route_input
        result = runner.invoke(app, ["ingest", "metrics", str(_METRICS)])
        assert route_input(result.output) == "devops-metrics-to-scorecard"

    def test_transcript_feeds_generate_pipeline(self, tmp_path):
        from pptgen.connectors import get_connector
        from pptgen.pipeline import generate_presentation
        out = get_connector("transcript").normalize(_TRANSCRIPT)
        result = generate_presentation(out.text, output_path=tmp_path / "out.pptx")
        assert result.stage == "rendered"
        assert (tmp_path / "out.pptx").exists()
