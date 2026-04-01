"""Unit tests for the batch generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptgen.orchestration import BatchItemResult, BatchResult, generate_batch
from pptgen.orchestration.batch_generator import BatchError, _discover_files


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_BATCH_TEXT = _FIXTURES / "batch" / "text"
_BATCH_ADO = _FIXTURES / "batch" / "ado"
_BATCH_METRICS = _FIXTURES / "batch" / "metrics"


# ---------------------------------------------------------------------------
# BatchResult / BatchItemResult structure
# ---------------------------------------------------------------------------

class TestBatchResultStructure:
    def test_batch_result_is_dataclass(self):
        r = BatchResult(total_files=0, succeeded=0, failed=0)
        assert r is not None

    def test_batch_result_fields(self):
        r = BatchResult(total_files=3, succeeded=2, failed=1)
        assert r.total_files == 3
        assert r.succeeded == 2
        assert r.failed == 1
        assert isinstance(r.outputs, list)
        assert isinstance(r.notes, list)

    def test_batch_item_result_fields(self):
        p = Path("some/file.txt")
        item = BatchItemResult(input_path=p)
        assert item.input_path == p
        assert item.output_path is None
        assert item.success is False
        assert item.error == ""
        assert item.artifact_paths is None


# ---------------------------------------------------------------------------
# Input directory validation
# ---------------------------------------------------------------------------

class TestInputDirValidation:
    def test_missing_dir_raises_batch_error(self, tmp_path):
        with pytest.raises(BatchError, match="not found"):
            generate_batch(tmp_path / "does_not_exist")

    def test_file_instead_of_dir_raises_batch_error(self, tmp_path):
        f = tmp_path / "not_a_dir.txt"
        f.write_text("hello")
        with pytest.raises(BatchError, match="not a directory"):
            generate_batch(f)

    def test_empty_dir_returns_zero_files(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        r = generate_batch(empty, output_dir=tmp_path / "out")
        assert r.total_files == 0
        assert r.succeeded == 0
        assert r.failed == 0

    def test_empty_dir_adds_note(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        r = generate_batch(empty, output_dir=tmp_path / "out")
        assert r.notes  # Should have "No files found" note


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

class TestFileDiscovery:
    def test_discovers_all_files(self, tmp_path):
        for name in ("c.txt", "a.txt", "b.txt"):
            (tmp_path / name).write_text("sprint backlog velocity")
        files = _discover_files(tmp_path)
        assert len(files) == 3

    def test_sorts_by_name(self, tmp_path):
        for name in ("c.txt", "a.txt", "b.txt"):
            (tmp_path / name).write_text("meeting notes")
        files = _discover_files(tmp_path)
        assert [f.name for f in files] == ["a.txt", "b.txt", "c.txt"]

    def test_skips_subdirectories(self, tmp_path):
        (tmp_path / "file.txt").write_text("text")
        (tmp_path / "subdir").mkdir()
        files = _discover_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "file.txt"


# ---------------------------------------------------------------------------
# Raw text batch mode
# ---------------------------------------------------------------------------

class TestRawTextBatch:
    def test_processes_two_files(self, tmp_path):
        r = generate_batch(_BATCH_TEXT, output_dir=tmp_path / "out")
        assert r.total_files == 2
        assert r.succeeded == 2
        assert r.failed == 0

    def test_output_files_exist(self, tmp_path):
        out = tmp_path / "out"
        r = generate_batch(_BATCH_TEXT, output_dir=out)
        for item in r.outputs:
            assert item.output_path is not None
            assert item.output_path.exists()

    def test_output_stems_match_input_stems(self, tmp_path):
        out = tmp_path / "out"
        r = generate_batch(_BATCH_TEXT, output_dir=out)
        for item in r.outputs:
            assert item.output_path.stem == item.input_path.stem

    def test_output_dir_created(self, tmp_path):
        out = tmp_path / "deep" / "nested" / "out"
        assert not out.exists()
        generate_batch(_BATCH_TEXT, output_dir=out)
        assert out.exists()

    def test_playbook_id_populated(self, tmp_path):
        r = generate_batch(_BATCH_TEXT, output_dir=tmp_path / "out")
        for item in r.outputs:
            assert item.playbook_id is not None

    def test_default_output_dir_used(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = generate_batch(_BATCH_TEXT)
        default = tmp_path / "output" / "batch"
        assert default.exists()
        assert r.succeeded == 2

    def test_processing_order_is_deterministic(self, tmp_path):
        r1 = generate_batch(_BATCH_TEXT, output_dir=tmp_path / "out1")
        r2 = generate_batch(_BATCH_TEXT, output_dir=tmp_path / "out2")
        names1 = [i.input_path.name for i in r1.outputs]
        names2 = [i.input_path.name for i in r2.outputs]
        assert names1 == names2


# ---------------------------------------------------------------------------
# ADO connector batch mode
# ---------------------------------------------------------------------------

class TestADOConnectorBatch:
    def test_processes_two_ado_files(self, tmp_path):
        r = generate_batch(_BATCH_ADO, output_dir=tmp_path / "out", connector_type="ado")
        assert r.total_files == 2
        assert r.succeeded == 2

    def test_ado_outputs_exist(self, tmp_path):
        out = tmp_path / "out"
        r = generate_batch(_BATCH_ADO, output_dir=out, connector_type="ado")
        for item in r.outputs:
            assert item.output_path.exists()

    def test_ado_playbook_is_weekly_delivery(self, tmp_path):
        r = generate_batch(_BATCH_ADO, output_dir=tmp_path / "out", connector_type="ado")
        for item in r.outputs:
            assert item.playbook_id == "ado-summary-to-weekly-delivery"

    def test_malformed_json_causes_per_file_failure(self, tmp_path):
        bad_dir = tmp_path / "ado_bad"
        bad_dir.mkdir()
        (bad_dir / "good.json").write_text(
            json.dumps({"sprint": "S1", "velocity": 10}), encoding="utf-8"
        )
        (bad_dir / "bad.json").write_text("{not valid json", encoding="utf-8")
        r = generate_batch(bad_dir, output_dir=tmp_path / "out", connector_type="ado")
        assert r.total_files == 2
        assert r.succeeded == 1
        assert r.failed == 1
        failed = next(i for i in r.outputs if not i.success)
        assert "bad.json" in str(failed.input_path)
        assert failed.error

    def test_batch_continues_after_one_failure(self, tmp_path):
        """Batch must not abort — succeeds on good file despite bad file."""
        bad_dir = tmp_path / "mixed"
        bad_dir.mkdir()
        # 'a_bad.json' sorts first; 'b_good.json' must still be processed
        (bad_dir / "a_bad.json").write_text("{invalid}", encoding="utf-8")
        (bad_dir / "b_good.json").write_text(
            json.dumps({"sprint": "S1", "velocity": 5}), encoding="utf-8"
        )
        r = generate_batch(bad_dir, output_dir=tmp_path / "out", connector_type="ado")
        assert r.succeeded == 1
        assert r.failed == 1
        good = next(i for i in r.outputs if i.success)
        assert "b_good.json" in str(good.input_path)


# ---------------------------------------------------------------------------
# Metrics connector batch mode
# ---------------------------------------------------------------------------

class TestMetricsConnectorBatch:
    def test_processes_one_metrics_file(self, tmp_path):
        r = generate_batch(_BATCH_METRICS, output_dir=tmp_path / "out", connector_type="metrics")
        assert r.total_files == 1
        assert r.succeeded == 1

    def test_metrics_playbook_is_scorecard(self, tmp_path):
        r = generate_batch(_BATCH_METRICS, output_dir=tmp_path / "out", connector_type="metrics")
        assert r.outputs[0].playbook_id == "devops-metrics-to-scorecard"


# ---------------------------------------------------------------------------
# Artifact export in batch
# ---------------------------------------------------------------------------

class TestBatchArtifacts:
    def test_artifacts_enabled_creates_per_file_dirs(self, tmp_path):
        out = tmp_path / "out"
        r = generate_batch(_BATCH_TEXT, output_dir=out, artifacts=True)
        for item in r.outputs:
            assert item.artifact_paths is not None
            stem = item.input_path.stem
            arts_dir = out / f"{stem}.artifacts"
            assert arts_dir.exists()

    def test_artifacts_contain_spec_json(self, tmp_path):
        out = tmp_path / "out"
        r = generate_batch(_BATCH_TEXT, output_dir=out, artifacts=True)
        for item in r.outputs:
            assert "spec" in item.artifact_paths
            assert Path(item.artifact_paths["spec"]).exists()

    def test_artifacts_disabled_by_default(self, tmp_path):
        r = generate_batch(_BATCH_TEXT, output_dir=tmp_path / "out")
        for item in r.outputs:
            assert item.artifact_paths is None

    def test_custom_artifacts_base_dir(self, tmp_path):
        out = tmp_path / "out"
        arts_base = tmp_path / "arts"
        r = generate_batch(
            _BATCH_TEXT, output_dir=out, artifacts=True, artifacts_base_dir=arts_base
        )
        for item in r.outputs:
            stem = item.input_path.stem
            assert (arts_base / f"{stem}.artifacts" / "spec.json").exists()


# ---------------------------------------------------------------------------
# Unknown connector type
# ---------------------------------------------------------------------------

class TestUnknownConnectorType:
    def test_unknown_connector_raises_batch_error(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        with pytest.raises(BatchError, match="Unknown connector"):
            generate_batch(d, connector_type="bad-connector")


# ---------------------------------------------------------------------------
# Mode and template passthrough
# ---------------------------------------------------------------------------

class TestModeAndTemplatePassthrough:
    def test_ai_mode_batch(self, tmp_path):
        r = generate_batch(_BATCH_TEXT, output_dir=tmp_path / "out", mode="ai")
        assert r.succeeded == 2

    def test_template_override_applied(self, tmp_path):
        r = generate_batch(
            _BATCH_TEXT,
            output_dir=tmp_path / "out",
            template_id="ops_review_v1",
        )
        assert r.succeeded == 2
