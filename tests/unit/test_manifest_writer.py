"""Tests for ManifestWriter."""
from __future__ import annotations

import json

import pytest

from pptgen.artifacts.manifest import ManifestWriter
from pptgen.artifacts.models import ArtifactRecord, ArtifactType
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.runs.models import RunRecord, RunSource, RunStatus


class TestManifestWriter:
    def test_writes_manifest_json(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        writer = ManifestWriter(storage)
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        path = writer.write(run, [])
        assert path.name == "manifest.json"
        assert path.exists()

    def test_manifest_contains_run_id(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        writer = ManifestWriter(storage)
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        path = writer.write(run, [])
        data = json.loads(path.read_text())
        assert data["run_id"] == run.run_id

    def test_manifest_lists_artifacts(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        writer = ManifestWriter(storage)
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        artifact = ArtifactRecord.create(
            run_id=run.run_id, artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path=f"runs/{run.run_id}/output.pptx",
            size_bytes=100, checksum="sha256:abc",
        )
        path = writer.write(run, [artifact])
        data = json.loads(path.read_text())
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["artifact_type"] == "pptx"

    def test_manifest_has_version(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        writer = ManifestWriter(storage)
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        path = writer.write(run, [])
        data = json.loads(path.read_text())
        assert data["manifest_version"] == "1.0"

    def test_manifest_includes_run_context_timings(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        writer = ManifestWriter(storage)
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        ctx = {"playbook_id": "ops_review", "timings": [{"stage": "planning", "ms": 100}]}
        path = writer.write(run, [], run_context_dict=ctx)
        data = json.loads(path.read_text())
        assert data["timings"][0]["stage"] == "planning"

    def test_manifest_empty_artifacts_list(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        writer = ManifestWriter(storage)
        run = RunRecord.create(source=RunSource.API_SYNC)
        run.status = RunStatus.SUCCEEDED
        path = writer.write(run, [])
        data = json.loads(path.read_text())
        assert data["artifacts"] == []
