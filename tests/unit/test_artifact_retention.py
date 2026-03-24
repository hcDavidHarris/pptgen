"""Tests for artifact retention policy enforcement."""
from __future__ import annotations

import pytest

from pptgen.artifacts.models import ArtifactRecord, ArtifactStatus, ArtifactType
from pptgen.artifacts.retention import RetentionManager
from pptgen.artifacts.sqlite_store import SQLiteArtifactStore
from pptgen.artifacts.storage import ArtifactStorage


@pytest.fixture
def retention_setup(tmp_path):
    db = tmp_path / "artifacts.db"
    store = SQLiteArtifactStore(db_path=db)
    storage = ArtifactStorage(base=tmp_path / "store")
    mgr = RetentionManager(store, storage)
    yield store, storage, mgr
    store.close()


class TestRetentionManager:
    def test_expires_old_medium_artifact(self, retention_setup):
        store, storage, mgr = retention_setup
        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=10, checksum="sha256:x",
        )
        store.register(art)
        counts = mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert counts["medium"] >= 1
        assert store.get(art.artifact_id).status == ArtifactStatus.EXPIRED

    def test_expires_old_longest_artifact(self, retention_setup):
        store, storage, mgr = retention_setup
        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path="runs/r/output.pptx",
            size_bytes=100, checksum="sha256:x",
        )
        store.register(art)
        counts = mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert counts["longest"] >= 1
        assert store.get(art.artifact_id).status == ArtifactStatus.EXPIRED

    def test_expires_old_shorter_artifact(self, retention_setup):
        store, storage, mgr = retention_setup
        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.LOG,
            filename="run.log", relative_path="runs/r/run.log",
            size_bytes=5, checksum="sha256:y",
        )
        store.register(art)
        counts = mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert counts["shorter"] >= 1
        assert store.get(art.artifact_id).status == ArtifactStatus.EXPIRED

    def test_does_not_expire_always_class(self, retention_setup):
        store, storage, mgr = retention_setup
        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.MANIFEST,
            filename="manifest.json", relative_path="runs/r/manifest.json",
            size_bytes=100, checksum="sha256:y",
        )
        store.register(art)
        mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert store.get(art.artifact_id).status == ArtifactStatus.PRESENT

    def test_deletes_physical_file(self, retention_setup):
        store, storage, mgr = retention_setup
        storage.ensure_run_dir("r")
        spec_abs = storage.resolve("runs/r/spec.json")
        spec_abs.parent.mkdir(parents=True, exist_ok=True)
        spec_abs.write_text("{}", encoding="utf-8")

        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=2, checksum="sha256:z",
        )
        store.register(art)
        mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert not spec_abs.exists()

    def test_returns_counts_by_class(self, retention_setup):
        store, storage, mgr = retention_setup
        # Register one of each expirable type
        for atype in (ArtifactType.PPTX, ArtifactType.SPEC, ArtifactType.LOG):
            store.register(ArtifactRecord.create(
                run_id="r", artifact_type=atype,
                filename=atype.value, relative_path=f"runs/r/{atype.value}",
                size_bytes=1, checksum="sha256:x",
            ))
        counts = mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert isinstance(counts, dict)
        assert "longest" in counts
        assert "medium" in counts
        assert "shorter" in counts

    def test_non_expired_artifact_not_touched(self, retention_setup):
        store, storage, mgr = retention_setup
        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=10, checksum="sha256:x",
        )
        store.register(art)
        # Long TTL — nothing should expire
        mgr.run_cleanup(longest_hours=9999, medium_hours=9999, shorter_hours=9999)
        assert store.get(art.artifact_id).status == ArtifactStatus.PRESENT

    def test_missing_file_still_marks_expired(self, retention_setup):
        store, storage, mgr = retention_setup
        art = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=10, checksum="sha256:x",
        )
        store.register(art)
        # File doesn't exist on disk — should still mark expired without error
        mgr.run_cleanup(longest_hours=0, medium_hours=0, shorter_hours=0)
        assert store.get(art.artifact_id).status == ArtifactStatus.EXPIRED
