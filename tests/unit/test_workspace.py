"""Tests for Workspace and WorkspaceManager (Stage 6A — PR 4)."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pptgen.runtime import Workspace, WorkspaceManager


# ---------------------------------------------------------------------------
# WorkspaceManager.create
# ---------------------------------------------------------------------------

class TestCreate:
    def test_create_returns_workspace(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws = mgr.create("run-001")
        assert isinstance(ws, Workspace)
        assert ws.run_id == "run-001"

    def test_create_root_dir_exists(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws = mgr.create("run-001")
        assert ws.root.exists()
        assert ws.root.is_dir()

    def test_create_root_is_child_of_base(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws = mgr.create("run-001")
        assert ws.root.parent == tmp_path

    def test_create_artifacts_dir_exists(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws = mgr.create("run-001")
        assert ws.artifacts_path.exists()
        assert ws.artifacts_path.is_dir()

    def test_create_is_idempotent(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws1 = mgr.create("run-001")
        ws2 = mgr.create("run-001")
        assert ws1.root == ws2.root
        assert ws1.root.exists()

    def test_create_base_not_exist_is_created(self, tmp_path):
        base = tmp_path / "nested" / "base"
        mgr = WorkspaceManager(base=base)
        ws = mgr.create("run-001")
        assert ws.root.exists()


# ---------------------------------------------------------------------------
# Workspace paths
# ---------------------------------------------------------------------------

class TestWorkspacePaths:
    def test_output_path_is_pptx(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws = mgr.create("run-abc")
        assert ws.output_path == ws.root / "output.pptx"

    def test_artifacts_path_is_subdirectory(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        ws = mgr.create("run-abc")
        assert ws.artifacts_path == ws.root / "artifacts"


# ---------------------------------------------------------------------------
# WorkspaceManager.get
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_existing_workspace(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("run-001")
        ws = mgr.get("run-001")
        assert ws is not None
        assert ws.run_id == "run-001"
        assert ws.root.exists()

    def test_get_nonexistent_returns_none(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        assert mgr.get("does-not-exist") is None

    def test_get_returns_correct_root(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("my-run")
        ws = mgr.get("my-run")
        assert ws is not None
        assert ws.root == tmp_path / "my-run"


# ---------------------------------------------------------------------------
# WorkspaceManager.cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_cleanup_removes_directory(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("run-del")
        assert (tmp_path / "run-del").exists()
        mgr.cleanup("run-del")
        assert not (tmp_path / "run-del").exists()

    def test_cleanup_nonexistent_is_safe(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.cleanup("never-existed")  # should not raise

    def test_cleanup_does_not_affect_other_workspaces(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("keep")
        mgr.create("delete")
        mgr.cleanup("delete")
        assert (tmp_path / "keep").exists()
        assert not (tmp_path / "delete").exists()


# ---------------------------------------------------------------------------
# WorkspaceManager.cleanup_older_than
# ---------------------------------------------------------------------------

class TestCleanupOlderThan:
    def test_returns_zero_when_base_not_exist(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path / "nonexistent")
        assert mgr.cleanup_older_than(24) == 0

    def test_returns_zero_when_nothing_stale(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("fresh")
        deleted = mgr.cleanup_older_than(24)
        assert deleted == 0
        assert (tmp_path / "fresh").exists()

    def test_deletes_stale_workspaces(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("stale")
        stale_dir = tmp_path / "stale"
        # Backdate mtime by 25 hours
        old_time = time.time() - 25 * 3600
        import os
        os.utime(stale_dir, (old_time, old_time))
        deleted = mgr.cleanup_older_than(24)
        assert deleted == 1
        assert not stale_dir.exists()

    def test_keeps_recent_workspaces(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.create("recent")
        deleted = mgr.cleanup_older_than(1)
        assert deleted == 0
        assert (tmp_path / "recent").exists()

    def test_returns_count_of_deleted(self, tmp_path):
        import os
        mgr = WorkspaceManager(base=tmp_path)
        for name in ("stale1", "stale2", "stale3"):
            mgr.create(name)
            old_time = time.time() - 25 * 3600
            os.utime(tmp_path / name, (old_time, old_time))
        mgr.create("fresh")
        deleted = mgr.cleanup_older_than(24)
        assert deleted == 3
        assert (tmp_path / "fresh").exists()


# ---------------------------------------------------------------------------
# WorkspaceManager.is_base_writable
# ---------------------------------------------------------------------------

class TestIsBaseWritable:
    def test_writable_base_returns_true(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path / "new_base")
        assert mgr.is_base_writable() is True

    def test_probe_file_cleaned_up(self, tmp_path):
        mgr = WorkspaceManager(base=tmp_path)
        mgr.is_base_writable()
        assert not (tmp_path / ".write_probe").exists()

    def test_unwritable_path_returns_false(self, tmp_path):
        # Simulate OSError by patching Path.touch
        mgr = WorkspaceManager(base=tmp_path)
        with patch("pathlib.Path.touch", side_effect=OSError("permission denied")):
            assert mgr.is_base_writable() is False


# ---------------------------------------------------------------------------
# WorkspaceManager.from_settings
# ---------------------------------------------------------------------------

class TestFromSettings:
    def test_from_settings_uses_workspace_base_path(self, tmp_path):
        from pptgen.config import RuntimeSettings
        settings = RuntimeSettings(workspace_base=str(tmp_path))
        mgr = WorkspaceManager.from_settings(settings)
        ws = mgr.create("run-123")
        assert ws.root.parent == tmp_path
