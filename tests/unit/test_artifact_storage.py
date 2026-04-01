"""Tests for ArtifactStorage."""
from __future__ import annotations

import pytest

from pptgen.artifacts.storage import ArtifactStorage, compute_checksum


class TestArtifactStorage:
    def test_promote_copies_file(self, tmp_path):
        src = tmp_path / "output.pptx"
        src.write_bytes(b"fake pptx content")
        storage = ArtifactStorage(base=tmp_path / "store")
        dest, checksum, size = storage.promote(src, "run1", "output.pptx")
        assert dest.exists()
        assert size == 17
        assert checksum.startswith("sha256:")

    def test_promote_creates_run_dir(self, tmp_path):
        src = tmp_path / "file.json"
        src.write_text("{}", encoding="utf-8")
        storage = ArtifactStorage(base=tmp_path / "store")
        storage.promote(src, "run1", "file.json")
        assert (tmp_path / "store" / "runs" / "run1").is_dir()

    def test_promote_file_content_preserved(self, tmp_path):
        src = tmp_path / "spec.json"
        src.write_bytes(b'{"key": "value"}')
        storage = ArtifactStorage(base=tmp_path / "store")
        dest, _, _ = storage.promote(src, "run1", "spec.json")
        assert dest.read_bytes() == b'{"key": "value"}'

    def test_relative_path(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        assert storage.relative_path("run1", "output.pptx") == "runs/run1/output.pptx"

    def test_resolve_path(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        resolved = storage.resolve("runs/run1/output.pptx")
        assert resolved == tmp_path / "store" / "runs" / "run1" / "output.pptx"

    def test_is_base_writable(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        assert storage.is_base_writable() is True

    def test_ensure_run_dir_creates_dir(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        d = storage.ensure_run_dir("myrun")
        assert d.is_dir()
        assert d == tmp_path / "store" / "runs" / "myrun"

    def test_run_dir_path(self, tmp_path):
        storage = ArtifactStorage(base=tmp_path / "store")
        assert storage.run_dir("run1") == tmp_path / "store" / "runs" / "run1"


class TestComputeChecksum:
    def test_checksum_starts_with_sha256(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"hello")
        c = compute_checksum(f)
        assert c.startswith("sha256:")

    def test_checksum_deterministic(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"hello")
        assert compute_checksum(f) == compute_checksum(f)

    def test_checksum_known_value(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"hello")
        assert compute_checksum(f) == (
            "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    def test_different_content_different_checksum(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_bytes(b"hello")
        f2.write_bytes(b"world")
        assert compute_checksum(f1) != compute_checksum(f2)
