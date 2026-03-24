"""Tests for ArtifactPromoter."""
from __future__ import annotations

import pytest

from pptgen.artifacts.models import ArtifactType
from pptgen.artifacts.promoter import ArtifactPromoter
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage
from pptgen.runs.models import RunRecord, RunSource, RunStatus
from pptgen.runs.sqlite_store import SQLiteRunStore


def _make_stores(tmp_path):
    db = tmp_path / "artifacts.db"
    storage = ArtifactStorage(base=tmp_path / "store")
    artifact_store = SQLiteArtifactStore(db_path=db)
    run_store = SQLiteRunStore(db_path=db)
    promoter = ArtifactPromoter(storage, artifact_store, run_store)
    return storage, artifact_store, run_store, promoter


class TestArtifactPromoter:
    def test_promote_pptx_file(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)
        (ws_root / "output.pptx").write_bytes(b"fake pptx")

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)

        promoted = promoter.promote(
            run=run,
            workspace_root=ws_root,
            artifacts_subdir=ws_root / "artifacts",
        )
        pptx_records = [a for a in promoted if a.artifact_type == ArtifactType.PPTX]
        assert len(pptx_records) == 1
        run_result = run_store.get(run.run_id)
        assert run_result.status == RunStatus.SUCCEEDED

    def test_promote_missing_artifacts_skipped(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)
        (ws_root / "output.pptx").write_bytes(b"fake pptx")
        # No artifacts subdir — spec.json etc are absent

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)

        promoted = promoter.promote(
            run=run,
            workspace_root=ws_root,
            artifacts_subdir=ws_root / "artifacts",
        )
        assert any(a.artifact_type == ArtifactType.PPTX for a in promoted)
        assert run_store.get(run.run_id).status == RunStatus.SUCCEEDED

    def test_promote_failed_run_records_error(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)

        promoter.promote(
            run=run,
            workspace_root=ws_root,
            artifacts_subdir=ws_root / "artifacts",
            error_category="planning",
            error_message="planning failed",
        )
        result = run_store.get(run.run_id)
        assert result.status == RunStatus.FAILED
        assert result.error_category == "planning"

    def test_manifest_registered_as_artifact(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)
        (ws_root / "output.pptx").write_bytes(b"fake")

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)

        promoted = promoter.promote(
            run=run,
            workspace_root=ws_root,
            artifacts_subdir=ws_root / "artifacts",
        )
        manifest_arts = [a for a in promoted if a.artifact_type == ArtifactType.MANIFEST]
        assert len(manifest_arts) == 1

    def test_promote_all_workspace_artifacts(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        artifacts_dir = ws_root / "artifacts"
        artifacts_dir.mkdir(parents=True)
        (ws_root / "output.pptx").write_bytes(b"pptx content")
        (artifacts_dir / "spec.json").write_text('{"spec": true}')
        (artifacts_dir / "slide_plan.json").write_text('{"plan": true}')
        (artifacts_dir / "deck_definition.json").write_text('{"deck": true}')

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)

        promoted = promoter.promote(
            run=run,
            workspace_root=ws_root,
            artifacts_subdir=artifacts_dir,
        )
        types = {a.artifact_type for a in promoted}
        assert ArtifactType.PPTX in types
        assert ArtifactType.SPEC in types
        assert ArtifactType.SLIDE_PLAN in types
        assert ArtifactType.DECK_DEFINITION in types
        assert ArtifactType.MANIFEST in types

    def test_run_manifest_path_set_on_success(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)
        (ws_root / "output.pptx").write_bytes(b"fake")

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)
        promoter.promote(run=run, workspace_root=ws_root,
                         artifacts_subdir=ws_root / "artifacts")
        result = run_store.get(run.run_id)
        assert result.manifest_path is not None
        assert "manifest.json" in result.manifest_path

    def test_pptx_promoted_to_durable_store(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)
        (ws_root / "output.pptx").write_bytes(b"fake pptx data")

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)
        promoter.promote(run=run, workspace_root=ws_root,
                         artifacts_subdir=ws_root / "artifacts")

        # File should exist in durable store
        durable = tmp_path / "store" / "runs" / run.run_id / "output.pptx"
        assert durable.exists()

    def test_no_workspace_files_all_missing(self, tmp_path):
        ws_root = tmp_path / "ws" / "run1"
        ws_root.mkdir(parents=True)
        # No files at all

        storage, artifact_store, run_store, promoter = _make_stores(tmp_path)
        run = RunRecord.create(source=RunSource.API_ASYNC)
        run_store.create(run)
        promoted = promoter.promote(run=run, workspace_root=ws_root,
                                    artifacts_subdir=ws_root / "artifacts")
        # Only manifest should be present (promotion of no files → SUCCEEDED with empty list + manifest)
        # But no pptx/spec etc
        pptx = [a for a in promoted if a.artifact_type == ArtifactType.PPTX]
        assert len(pptx) == 0
        # Run still succeeds (no error_category passed)
        assert run_store.get(run.run_id).status == RunStatus.SUCCEEDED
