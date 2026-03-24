"""Durable artifact filesystem storage."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


def compute_checksum(path: Path) -> str:
    """Return SHA-256 hex digest prefixed with 'sha256:'."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


class ArtifactStorage:
    """Manages the durable artifact filesystem store.

    Durable layout::

        {base}/
          runs/
            {run_id}/
              output.pptx
              spec.json
              slide_plan.json
              deck_definition.json
              manifest.json
    """

    def __init__(self, base: Path) -> None:
        self._base = base

    def run_dir(self, run_id: str) -> Path:
        return self._base / "runs" / run_id

    def ensure_run_dir(self, run_id: str) -> Path:
        d = self.run_dir(run_id)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def promote(self, src: Path, run_id: str, filename: str) -> tuple[Path, str, int]:
        """Copy src to durable run dir. Returns (dest_path, checksum, size_bytes)."""
        run_dir = self.ensure_run_dir(run_id)
        dest = run_dir / filename
        shutil.copy2(str(src), str(dest))
        checksum = compute_checksum(dest)
        size_bytes = dest.stat().st_size
        return dest, checksum, size_bytes

    def relative_path(self, run_id: str, filename: str) -> str:
        """Return path relative to artifact store base."""
        return f"runs/{run_id}/{filename}"

    def resolve(self, relative_path: str) -> Path:
        """Resolve a relative_path to an absolute filesystem path."""
        return self._base / relative_path

    def is_base_writable(self) -> bool:
        try:
            self._base.mkdir(parents=True, exist_ok=True)
            probe = self._base / ".write_probe"
            probe.touch()
            probe.unlink()
            return True
        except OSError:
            return False

    @classmethod
    def from_settings(cls, settings) -> ArtifactStorage:
        return cls(base=settings.artifact_store_path)
