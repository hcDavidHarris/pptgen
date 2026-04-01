"""Artifact domain models for Stage 6C."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ArtifactType(str, Enum):
    PPTX = "pptx"
    SPEC = "spec"
    SLIDE_PLAN = "slide_plan"
    DECK_DEFINITION = "deck_definition"
    MANIFEST = "manifest"
    LOG = "log"
    DIAGNOSTIC = "diagnostic"


class ArtifactVisibility(str, Enum):
    DOWNLOADABLE = "downloadable"   # pptx — exposed via download API
    INTERNAL = "internal"           # all others — metadata only


class ArtifactRetentionClass(str, Enum):
    ALWAYS = "always"       # manifest — never auto-deleted
    LONGEST = "longest"     # pptx — 7 days default
    MEDIUM = "medium"       # spec, slide_plan, deck_definition — 3 days default
    SHORTER = "shorter"     # logs, diagnostics — 1 day default


class ArtifactStatus(str, Enum):
    PRESENT = "present"
    DELETED = "deleted"
    EXPIRED = "expired"


# Policy table: type → (visibility, retention_class, is_final_output, mime_type)
ARTIFACT_POLICY: dict[ArtifactType, tuple] = {
    ArtifactType.PPTX: (
        ArtifactVisibility.DOWNLOADABLE,
        ArtifactRetentionClass.LONGEST,
        True,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    ArtifactType.MANIFEST: (
        ArtifactVisibility.INTERNAL,
        ArtifactRetentionClass.ALWAYS,
        False,
        "application/json",
    ),
    ArtifactType.SPEC: (
        ArtifactVisibility.INTERNAL,
        ArtifactRetentionClass.MEDIUM,
        False,
        "application/json",
    ),
    ArtifactType.SLIDE_PLAN: (
        ArtifactVisibility.INTERNAL,
        ArtifactRetentionClass.MEDIUM,
        False,
        "application/json",
    ),
    ArtifactType.DECK_DEFINITION: (
        ArtifactVisibility.INTERNAL,
        ArtifactRetentionClass.MEDIUM,
        False,
        "application/json",
    ),
    ArtifactType.LOG: (
        ArtifactVisibility.INTERNAL,
        ArtifactRetentionClass.SHORTER,
        False,
        "text/plain",
    ),
    ArtifactType.DIAGNOSTIC: (
        ArtifactVisibility.INTERNAL,
        ArtifactRetentionClass.SHORTER,
        False,
        "application/json",
    ),
}


@dataclass
class ArtifactRecord:
    artifact_id: str
    run_id: str
    artifact_type: ArtifactType
    filename: str
    relative_path: str          # relative to artifact_store_base
    mime_type: str
    size_bytes: int
    checksum: str               # "sha256:<hex>"
    is_final_output: bool
    visibility: ArtifactVisibility
    retention_class: ArtifactRetentionClass
    status: ArtifactStatus
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    @classmethod
    def create(
        cls,
        run_id: str,
        artifact_type: ArtifactType,
        filename: str,
        relative_path: str,
        size_bytes: int,
        checksum: str,
    ) -> ArtifactRecord:
        vis, ret, final, mime = ARTIFACT_POLICY[artifact_type]
        return cls(
            artifact_id=uuid.uuid4().hex,
            run_id=run_id,
            artifact_type=artifact_type,
            filename=filename,
            relative_path=relative_path,
            mime_type=mime,
            size_bytes=size_bytes,
            checksum=checksum,
            is_final_output=final,
            visibility=vis,
            retention_class=ret,
            status=ArtifactStatus.PRESENT,
        )
