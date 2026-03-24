"""Manifest writer for run artifact inventories."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..runs.models import RunRecord
from .models import ArtifactRecord
from .storage import ArtifactStorage


class ManifestWriter:
    def __init__(self, storage: ArtifactStorage) -> None:
        self._storage = storage

    def write(
        self,
        run: RunRecord,
        artifacts: list[ArtifactRecord],
        run_context_dict: Optional[dict] = None,
    ) -> Path:
        """Write manifest.json to durable storage. Returns absolute path."""
        manifest: dict[str, Any] = {
            "manifest_version": "1.0",
            "run_id": run.run_id,
            "job_id": run.job_id,
            "status": run.status.value,
            "source": run.source.value,
            "mode": run.mode,
            "template_id": run.template_id,
            "playbook_id": run.playbook_id,
            "profile": run.profile,
            "config_fingerprint": run.config_fingerprint,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "total_ms": run.total_ms,
            "error_category": run.error_category,
            "error_message": run.error_message,
            "timings": run_context_dict.get("timings", []) if run_context_dict else [],
            "artifacts": [
                {
                    "artifact_id": a.artifact_id,
                    "artifact_type": a.artifact_type.value,
                    "filename": a.filename,
                    "relative_path": a.relative_path,
                    "mime_type": a.mime_type,
                    "size_bytes": a.size_bytes,
                    "checksum": a.checksum,
                    "is_final_output": a.is_final_output,
                    "visibility": a.visibility.value,
                    "retention_class": a.retention_class.value,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat(),
                }
                for a in artifacts
            ],
        }
        run_dir = self._storage.ensure_run_dir(run.run_id)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return manifest_path
