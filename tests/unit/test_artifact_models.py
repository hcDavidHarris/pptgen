"""Tests for artifact domain models."""
from __future__ import annotations

import pytest

from pptgen.artifacts.models import (
    ARTIFACT_POLICY,
    ArtifactRecord,
    ArtifactRetentionClass,
    ArtifactStatus,
    ArtifactType,
    ArtifactVisibility,
)


class TestArtifactRecord:
    def test_create_pptx_is_downloadable(self):
        rec = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path="runs/run1/output.pptx",
            size_bytes=1024, checksum="sha256:abc",
        )
        assert rec.visibility == ArtifactVisibility.DOWNLOADABLE

    def test_create_pptx_is_final_output(self):
        rec = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path="runs/run1/output.pptx",
            size_bytes=1024, checksum="sha256:abc",
        )
        assert rec.is_final_output is True

    def test_create_spec_is_internal(self):
        rec = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/run1/spec.json",
            size_bytes=512, checksum="sha256:def",
        )
        assert rec.visibility == ArtifactVisibility.INTERNAL

    def test_create_manifest_retention_always(self):
        rec = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.MANIFEST,
            filename="manifest.json", relative_path="runs/run1/manifest.json",
            size_bytes=256, checksum="sha256:ghi",
        )
        assert rec.retention_class == ArtifactRetentionClass.ALWAYS

    def test_create_pptx_retention_longest(self):
        rec = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.PPTX,
            filename="output.pptx", relative_path="runs/run1/output.pptx",
            size_bytes=1024, checksum="sha256:abc",
        )
        assert rec.retention_class == ArtifactRetentionClass.LONGEST

    def test_create_status_is_present(self):
        rec = ArtifactRecord.create(
            run_id="run1", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/run1/spec.json",
            size_bytes=512, checksum="sha256:def",
        )
        assert rec.status == ArtifactStatus.PRESENT

    def test_create_generates_unique_artifact_ids(self):
        r1 = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=1, checksum="sha256:x",
        )
        r2 = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=1, checksum="sha256:x",
        )
        assert r1.artifact_id != r2.artifact_id

    def test_all_artifact_types_have_policy(self):
        for at in ArtifactType:
            assert at in ARTIFACT_POLICY

    def test_create_spec_not_final_output(self):
        rec = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SPEC,
            filename="spec.json", relative_path="runs/r/spec.json",
            size_bytes=1, checksum="sha256:x",
        )
        assert rec.is_final_output is False

    def test_create_slide_plan_retention_medium(self):
        rec = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.SLIDE_PLAN,
            filename="slide_plan.json", relative_path="runs/r/slide_plan.json",
            size_bytes=1, checksum="sha256:x",
        )
        assert rec.retention_class == ArtifactRetentionClass.MEDIUM

    def test_create_log_retention_shorter(self):
        rec = ArtifactRecord.create(
            run_id="r", artifact_type=ArtifactType.LOG,
            filename="run.log", relative_path="runs/r/run.log",
            size_bytes=1, checksum="sha256:x",
        )
        assert rec.retention_class == ArtifactRetentionClass.SHORTER
