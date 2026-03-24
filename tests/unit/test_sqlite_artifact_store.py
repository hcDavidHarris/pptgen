"""Tests for SQLiteArtifactStore."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pptgen.artifacts.models import ArtifactRecord, ArtifactStatus, ArtifactType
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteArtifactStore(db_path=tmp_path / "artifacts.db")
    yield s
    s.close()


def _make_artifact(run_id: str, atype: ArtifactType = ArtifactType.SPEC) -> ArtifactRecord:
    return ArtifactRecord.create(
        run_id=run_id,
        artifact_type=atype,
        filename=f"{atype.value}.json",
        relative_path=f"runs/{run_id}/{atype.value}.json",
        size_bytes=100,
        checksum="sha256:abc",
    )


class TestRegisterAndGet:
    def test_register_then_get(self, store):
        art = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path="runs/run1/output.pptx",
            size_bytes=1024, checksum="sha256:abc",
        )
        store.register(art)
        fetched = store.get(art.artifact_id)
        assert fetched.artifact_id == art.artifact_id
        assert fetched.status == ArtifactStatus.PRESENT

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("nonexistent") is None

    def test_register_preserves_type(self, store):
        art = _make_artifact("run1", ArtifactType.PPTX)
        store.register(art)
        assert store.get(art.artifact_id).artifact_type == ArtifactType.PPTX

    def test_register_preserves_checksum(self, store):
        art = _make_artifact("run1")
        store.register(art)
        assert store.get(art.artifact_id).checksum == art.checksum


class TestListForRun:
    def test_list_returns_all_artifacts_for_run(self, store):
        for atype in (ArtifactType.PPTX, ArtifactType.SPEC):
            store.register(_make_artifact("run1", atype))
        results = store.list_for_run("run1")
        assert len(results) == 2

    def test_list_filters_by_run_id(self, store):
        store.register(_make_artifact("run1"))
        store.register(_make_artifact("run2"))
        assert len(store.list_for_run("run1")) == 1
        assert len(store.list_for_run("run2")) == 1

    def test_list_empty_run_returns_empty(self, store):
        assert store.list_for_run("nonexistent") == []


class TestUpdateStatus:
    def test_update_status_to_expired(self, store):
        art = _make_artifact("run1")
        store.register(art)
        store.update_status(art.artifact_id, ArtifactStatus.EXPIRED)
        assert store.get(art.artifact_id).status == ArtifactStatus.EXPIRED

    def test_update_status_to_deleted(self, store):
        art = _make_artifact("run1")
        store.register(art)
        store.update_status(art.artifact_id, ArtifactStatus.DELETED)
        assert store.get(art.artifact_id).status == ArtifactStatus.DELETED


class TestListExpired:
    def test_returns_artifacts_older_than_cutoff(self, store):
        art = _make_artifact("run1")
        store.register(art)
        # Use future cutoff — all records qualify
        expired = store.list_expired(
            "medium", datetime.now(tz=timezone.utc) + timedelta(days=1)
        )
        assert any(a.artifact_id == art.artifact_id for a in expired)

    def test_does_not_return_future_artifacts(self, store):
        art = _make_artifact("run1")
        store.register(art)
        # Past cutoff — no records qualify
        expired = store.list_expired(
            "medium", datetime.now(tz=timezone.utc) - timedelta(days=1)
        )
        assert not any(a.artifact_id == art.artifact_id for a in expired)

    def test_filters_by_retention_class(self, store):
        spec = _make_artifact("run1", ArtifactType.SPEC)   # medium
        pptx = _make_artifact("run1", ArtifactType.PPTX)   # longest
        store.register(spec)
        store.register(pptx)
        cutoff = datetime.now(tz=timezone.utc) + timedelta(days=1)
        medium_expired = store.list_expired("medium", cutoff)
        ids = {a.artifact_id for a in medium_expired}
        assert spec.artifact_id in ids
        assert pptx.artifact_id not in ids

    def test_does_not_return_already_expired(self, store):
        art = _make_artifact("run1")
        store.register(art)
        store.update_status(art.artifact_id, ArtifactStatus.EXPIRED)
        expired = store.list_expired(
            "medium", datetime.now(tz=timezone.utc) + timedelta(days=1)
        )
        assert not any(a.artifact_id == art.artifact_id for a in expired)


class TestFromSettings:
    def test_from_settings(self, tmp_path):
        from pptgen.config import RuntimeSettings
        settings = RuntimeSettings(
            workspace_base=str(tmp_path / "ws"),
            artifact_db_path=str(tmp_path / "artifacts.db"),
        )
        store = SQLiteArtifactStore.from_settings(settings)
        try:
            art = _make_artifact("run1")
            store.register(art)
            assert store.get(art.artifact_id) is not None
        finally:
            store.close()
