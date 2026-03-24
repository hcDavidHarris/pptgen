"""ArtifactPromoter — orchestrates workspace-to-durable promotion."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..runs.models import RunRecord, RunStatus
from ..runs.store import AbstractRunStore
from .manifest import ManifestWriter
from .models import ArtifactRecord, ArtifactType
from .sqlite_store import SQLiteArtifactStore
from .storage import ArtifactStorage, compute_checksum

logger = logging.getLogger(__name__)

# Maps workspace filenames to ArtifactType
# (filename_in_workspace, artifact_type, is_in_artifacts_subdir)
_WORKSPACE_ARTIFACTS: list[tuple[str, ArtifactType, bool]] = [
    ("output.pptx",            ArtifactType.PPTX,             False),
    ("spec.json",              ArtifactType.SPEC,              True),
    ("slide_plan.json",        ArtifactType.SLIDE_PLAN,        True),
    ("deck_definition.json",   ArtifactType.DECK_DEFINITION,   True),
]


class ArtifactPromoter:
    """Copies workspace artifacts to durable storage, registers metadata,
    writes manifest, and finalizes the run record.

    Promotion is best-effort: if individual files are missing (e.g., no
    artifacts were generated), they are skipped. Only if ALL promotions
    fail does the run end in FAILED status.
    """

    def __init__(
        self,
        storage: ArtifactStorage,
        artifact_store: SQLiteArtifactStore,
        run_store: AbstractRunStore,
    ) -> None:
        self._storage = storage
        self._artifact_store = artifact_store
        self._run_store = run_store
        self._manifest_writer = ManifestWriter(storage)

    def promote(
        self,
        run: RunRecord,
        workspace_root: Path,
        artifacts_subdir: Path,
        run_context_dict: Optional[dict] = None,
        error_category: Optional[str] = None,
        error_message: Optional[str] = None,
        total_ms: Optional[float] = None,
    ) -> list[ArtifactRecord]:
        """Promote workspace artifacts to durable storage.

        Returns list of successfully registered ArtifactRecords.
        Partial failure: some artifacts may be registered even on failure.
        Run status is updated to SUCCEEDED or FAILED based on final state.
        """
        promoted: list[ArtifactRecord] = []
        promotion_errors: list[str] = []

        for filename, artifact_type, in_subdir in _WORKSPACE_ARTIFACTS:
            src = (artifacts_subdir / filename) if in_subdir else (workspace_root / filename)
            if not src.exists():
                logger.debug("Artifact not found, skipping: %s", src)
                continue
            try:
                dest, checksum, size = self._storage.promote(
                    src, run.run_id, filename
                )
                rel_path = self._storage.relative_path(run.run_id, filename)
                record = ArtifactRecord.create(
                    run_id=run.run_id,
                    artifact_type=artifact_type,
                    filename=filename,
                    relative_path=rel_path,
                    size_bytes=size,
                    checksum=checksum,
                )
                self._artifact_store.register(record)
                promoted.append(record)
                logger.debug("Promoted %s (%d bytes)", filename, size)
            except Exception as exc:
                promotion_errors.append(f"{filename}: {exc}")
                logger.warning("Failed to promote %s: %s", filename, exc)

        # Determine final run status
        if error_category or error_message:
            final_status = RunStatus.FAILED
        elif promotion_errors and not promoted:
            final_status = RunStatus.FAILED
            error_category = error_category or "workspace"
            error_message = error_message or "; ".join(promotion_errors)
        else:
            final_status = RunStatus.SUCCEEDED

        # Write manifest (always attempt, even on failure)
        manifest_path_rel: Optional[str] = None
        try:
            run.status = final_status
            run.completed_at = datetime.now(tz=timezone.utc)
            run.total_ms = total_ms
            run.error_category = error_category
            run.error_message = error_message
            manifest_abs = self._manifest_writer.write(
                run, promoted, run_context_dict=run_context_dict
            )
            manifest_path_rel = self._storage.relative_path(
                run.run_id, "manifest.json"
            )
            # Register manifest as artifact too
            manifest_record = ArtifactRecord.create(
                run_id=run.run_id,
                artifact_type=ArtifactType.MANIFEST,
                filename="manifest.json",
                relative_path=manifest_path_rel,
                size_bytes=manifest_abs.stat().st_size,
                checksum=compute_checksum(manifest_abs),
            )
            self._artifact_store.register(manifest_record)
            promoted.append(manifest_record)
        except Exception as exc:
            logger.warning("Failed to write manifest for run %s: %s", run.run_id, exc)

        # Finalize run record
        self._run_store.update_status(
            run.run_id,
            final_status,
            playbook_id=run_context_dict.get("playbook_id") if run_context_dict else None,
            error_category=error_category,
            error_message=error_message,
            total_ms=total_ms,
            manifest_path=manifest_path_rel,
        )

        return promoted

    @classmethod
    def from_settings(cls, settings, artifact_store, run_store) -> ArtifactPromoter:
        storage = ArtifactStorage.from_settings(settings)
        return cls(
            storage=storage,
            artifact_store=artifact_store,
            run_store=run_store,
        )
