"""Per-run workspace management for the pptgen platform.

Each pipeline execution gets its own isolated workspace directory under a
configurable base path.  :class:`WorkspaceManager` handles creation, retrieval,
cleanup, and TTL-based pruning.

Usage::

    from pptgen.config import get_settings
    from pptgen.runtime.workspace import WorkspaceManager

    manager = WorkspaceManager.from_settings(get_settings())
    ws = manager.create("abc123")
    print(ws.output_path)       # …/pptgen_api/abc123/output.pptx
    print(ws.artifacts_path)    # …/pptgen_api/abc123/artifacts/

Cleanup::

    manager.cleanup("abc123")              # delete one workspace
    deleted = manager.cleanup_older_than(24)  # prune workspaces older than 24 h
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Workspace:
    """Reference to one per-run workspace directory.

    Attributes:
        run_id: The unique run identifier that names this workspace.
        root:   Absolute path to the workspace root directory.
    """

    run_id: str
    root: Path

    @property
    def output_path(self) -> Path:
        """Path where the generated ``.pptx`` file should be written."""
        return self.root / "output.pptx"

    @property
    def artifacts_path(self) -> Path:
        """Path to the ``artifacts/`` subdirectory for supplementary exports."""
        return self.root / "artifacts"


class WorkspaceManager:
    """Creates and manages per-run workspace directories.

    Args:
        base: Absolute path to the workspace root directory.  All per-run
              directories will be created as immediate children of *base*.
    """

    def __init__(self, base: Path) -> None:
        self._base = base

    # ------------------------------------------------------------------
    # Workspace lifecycle
    # ------------------------------------------------------------------

    def create(self, run_id: str) -> Workspace:
        """Create a new workspace for *run_id* and return it.

        Creates ``<base>/<run_id>/`` and ``<base>/<run_id>/artifacts/``.
        Idempotent: safe to call multiple times for the same *run_id*.
        """
        root = self._base / run_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "artifacts").mkdir(exist_ok=True)
        return Workspace(run_id=run_id, root=root)

    def get(self, run_id: str) -> Workspace | None:
        """Return the :class:`Workspace` for *run_id*, or ``None`` if it does
        not exist on disk."""
        root = self._base / run_id
        if root.exists():
            return Workspace(run_id=run_id, root=root)
        return None

    def cleanup(self, run_id: str) -> None:
        """Delete the workspace for *run_id*.

        Safe to call even if the workspace does not exist.
        """
        root = self._base / run_id
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)

    def cleanup_older_than(self, hours: int) -> int:
        """Delete all workspaces whose directory mtime is older than *hours*.

        Returns:
            Number of workspaces deleted.
        """
        if not self._base.exists():
            return 0
        cutoff = time.time() - hours * 3600
        deleted = 0
        for child in self._base.iterdir():
            if child.is_dir() and child.stat().st_mtime < cutoff:
                shutil.rmtree(child, ignore_errors=True)
                deleted += 1
        return deleted

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_base_writable(self) -> bool:
        """Return ``True`` if the workspace base directory is writable.

        Attempts to create the base directory if it does not exist, then
        writes and removes a probe file.  Returns ``False`` on any
        :exc:`OSError`.
        """
        try:
            self._base.mkdir(parents=True, exist_ok=True)
            probe = self._base / ".write_probe"
            probe.touch()
            probe.unlink()
            return True
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_settings(cls, settings) -> WorkspaceManager:
        """Construct a :class:`WorkspaceManager` from a
        :class:`~pptgen.config.RuntimeSettings` instance."""
        return cls(base=settings.workspace_base_path)
