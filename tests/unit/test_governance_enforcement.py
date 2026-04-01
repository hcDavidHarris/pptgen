"""Unit tests for Phase 10B — runtime governance enforcement.

Covers:
- enforce_artifact_lifecycle() happy path (APPROVED — no-op)
- enforce_artifact_lifecycle() DRAFT raises GovernanceViolationError when allow_draft=False
- enforce_artifact_lifecycle() DRAFT is permitted when allow_draft=True
- enforce_artifact_lifecycle() DEPRECATED appends to warnings list
- enforce_artifact_lifecycle() DEPRECATED does not raise
- enforce_artifact_lifecycle() unknown version is a no-op
- enforce_artifact_lifecycle() unknown artifact type is a no-op
- enforcement wired into _resolve_primitive (DRAFT blocked by default)
- enforcement wired into _resolve_layout (DRAFT blocked by default)
- enforcement wired into asset resolution (DRAFT blocked by default)
- allow_draft_artifacts=True setting permits DRAFT at pipeline level
- DEPRECATED primitive emits governance_warnings, does not raise
- PipelineResult.governance_warnings is empty list when no issues
- PipelineResult.governance_warnings contains warnings when DEPRECATED artifacts used
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.config import RuntimeSettings, override_settings
from pptgen.design_system import (
    DesignSystemRegistry,
    GovernanceViolationError,
)


DESIGN_SYSTEM_PATH = Path("design_system")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_primitive_yaml(
    primitive_id: str = "test_prim",
    version: str = "1.0.0",
    status: str = "approved",
    deprecation_reason: str | None = None,
) -> str:
    reason_line = (
        f"  deprecation_reason: \"{deprecation_reason}\"\n"
        if deprecation_reason is not None
        else ""
    )
    return (
        f"schema_version: 1\n"
        f"primitive_id: {primitive_id}\n"
        f"version: \"{version}\"\n"
        f"layout_id: single_column\n"
        f"constraints:\n"
        f"  allow_extra_content: false\n"
        f"slots:\n"
        f"  title:\n"
        f"    required: true\n"
        f"    content_type: string\n"
        f"    maps_to: content\n"
        f"    description: \"Heading\"\n"
        f"governance:\n"
        f"  status: {status}\n"
        f"{reason_line}"
    )


def _make_registry_with_prim(tmp_path: Path, **kwargs) -> DesignSystemRegistry:
    ds = tmp_path / "ds"
    (ds / "primitives").mkdir(parents=True)
    primitive_id = kwargs.get("primitive_id", "test_prim")
    (ds / "primitives" / f"{primitive_id}.yaml").write_text(
        _make_primitive_yaml(**kwargs), encoding="utf-8"
    )
    return DesignSystemRegistry(ds)


# ---------------------------------------------------------------------------
# TestEnforceArtifactLifecycle — direct registry method tests
# ---------------------------------------------------------------------------


class TestEnforceArtifactLifecycle:
    def test_approved_no_op(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="approved")
        warnings: list[str] = []
        # Must not raise, must not append anything
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "1.0.0", warnings=warnings
        )
        assert warnings == []

    def test_draft_raises_by_default(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="0.1.0", status="draft")
        with pytest.raises(GovernanceViolationError, match="DRAFT"):
            reg.enforce_artifact_lifecycle("primitive", "test_prim", "0.1.0")

    def test_draft_permitted_when_allow_draft_true(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="0.1.0", status="draft")
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "0.1.0", allow_draft=True, warnings=warnings
        )
        assert warnings == []  # DRAFT+allowed is clean

    def test_deprecated_appends_warning(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="deprecated")
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "1.0.0", warnings=warnings
        )
        assert len(warnings) == 1
        assert "DEPRECATED" in warnings[0]
        assert "test_prim" in warnings[0]

    def test_deprecated_with_reason_in_warning(self, tmp_path):
        reg = _make_registry_with_prim(
            tmp_path, version="1.0.0", status="deprecated",
            deprecation_reason="Use new_prim instead."
        )
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "1.0.0", warnings=warnings
        )
        assert "Use new_prim instead." in warnings[0]

    def test_deprecated_does_not_raise(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="deprecated")
        # Must not raise even with allow_draft=False (deprecated is not draft)
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "1.0.0", allow_draft=False
        )

    def test_unknown_version_is_noop(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="draft")
        warnings: list[str] = []
        # Version 9.9.9 doesn't exist → no-op, no raise
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "9.9.9", warnings=warnings
        )
        assert warnings == []

    def test_unknown_artifact_type_is_noop(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "widget", "something", "1.0.0", warnings=warnings
        )
        assert warnings == []

    def test_unknown_artifact_id_is_noop(self):
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "primitive", "ghost_prim", "1.0.0", warnings=warnings
        )
        assert warnings == []

    def test_warnings_none_does_not_raise_for_deprecated(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="deprecated")
        # warnings=None → silently discard deprecation notices
        reg.enforce_artifact_lifecycle("primitive", "test_prim", "1.0.0", warnings=None)

    def test_error_message_contains_artifact_type(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="0.5.0", status="draft")
        with pytest.raises(GovernanceViolationError, match="(?i)primitive"):
            reg.enforce_artifact_lifecycle("primitive", "test_prim", "0.5.0")

    def test_error_message_contains_artifact_id(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="0.5.0", status="draft")
        with pytest.raises(GovernanceViolationError, match="test_prim"):
            reg.enforce_artifact_lifecycle("primitive", "test_prim", "0.5.0")

    def test_error_message_contains_version(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="0.5.0", status="draft")
        with pytest.raises(GovernanceViolationError, match="0.5.0"):
            reg.enforce_artifact_lifecycle("primitive", "test_prim", "0.5.0")

    def test_multiple_deprecated_calls_accumulate(self, tmp_path):
        reg = _make_registry_with_prim(tmp_path, version="1.0.0", status="deprecated")
        # Load governance once
        reg.enforce_artifact_lifecycle("primitive", "test_prim", "1.0.0")
        # Second call on same (idempotent load) still works
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "primitive", "test_prim", "1.0.0", warnings=warnings
        )
        assert len(warnings) == 1

    def test_real_approved_artifact_no_warning(self):
        """Real design_system artifacts default to APPROVED when no governance block."""
        reg = DesignSystemRegistry(DESIGN_SYSTEM_PATH)
        reg.get_primitive("bullet_slide")  # warm cache
        warnings: list[str] = []
        reg.enforce_artifact_lifecycle(
            "primitive", "bullet_slide", "1.0.0", warnings=warnings
        )
        assert warnings == []


# ---------------------------------------------------------------------------
# TestPipelineEnforcement — enforcement wired into generate_presentation()
# ---------------------------------------------------------------------------


class TestPipelineEnforcement:
    """These tests use a tmp design_system to inject DRAFT/DEPRECATED status."""

    def _make_full_ds(self, tmp_path: Path, status: str = "approved") -> Path:
        """Create a minimal design_system/ with all required artifacts."""
        ds = tmp_path / "ds"
        # primitives
        (ds / "primitives").mkdir(parents=True)
        (ds / "primitives" / "title_slide.yaml").write_text(
            f"schema_version: 1\n"
            f"primitive_id: title_slide\n"
            f"version: \"1.0.0\"\n"
            f"layout_id: single_column\n"
            f"constraints:\n  allow_extra_content: true\n"
            f"slots:\n"
            f"  title:\n"
            f"    required: false\n"
            f"    content_type: string\n"
            f"    maps_to: content\n"
            f"    description: \"Title\"\n"
            f"governance:\n  status: {status}\n",
            encoding="utf-8",
        )
        # layouts
        (ds / "layouts").mkdir(parents=True)
        (ds / "layouts" / "single_column.yaml").write_text(
            "schema_version: 1\n"
            "layout_id: single_column\n"
            "version: \"1.0.0\"\n"
            "regions:\n"
            "  content:\n"
            "    required: false\n"
            "    label: Main content\n",
            encoding="utf-8",
        )
        # tokens
        (ds / "tokens").mkdir(parents=True)
        (ds / "tokens" / "base_tokens.yaml").write_text(
            "schema_version: 1\n"
            "version: \"1.0.0\"\n"
            "tokens:\n  color.primary: \"#000000\"\n",
            encoding="utf-8",
        )
        # brands
        (ds / "brands").mkdir(parents=True)
        (ds / "brands" / "default.yaml").write_text(
            "schema_version: 1\n"
            "brand_id: default\n"
            "version: \"1.0.0\"\n"
            "token_overrides: {}\n",
            encoding="utf-8",
        )
        # themes
        (ds / "themes").mkdir(parents=True)
        (ds / "themes" / "default.yaml").write_text(
            "schema_version: 1\n"
            "theme_id: default\n"
            "version: \"1.0.0\"\n"
            "brand_id: default\n",
            encoding="utf-8",
        )
        # assets (empty dir so asset resolver doesn't error)
        (ds / "assets").mkdir(parents=True)
        return ds

    # The pipeline resolves governance for TOP-LEVEL `primitive:` keys
    # (deck_definition.get("primitive")).  Per-slide `primitive:` keys inside
    # the `slides:` list are normalised at render time, not at resolution time.
    # These tests use a structured deck with a top-level primitive declaration.

    def _deck_yaml_with_top_level_primitive(self) -> str:
        """Structured deck YAML with a top-level primitive: key."""
        return (
            "primitive: title_slide\n"
            "content:\n"
            "  title: Hello\n"
            "slides:\n"
            "  - primitive: title_slide\n"
            "    content:\n"
            "      title: Slide 1\n"
        )

    def test_draft_primitive_blocked_by_default(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import PipelineError, generate_presentation

        ds = self._make_full_ds(tmp_path, status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=False,
        ))
        try:
            with pytest.raises(PipelineError, match="DRAFT"):
                generate_presentation(self._deck_yaml_with_top_level_primitive())
        finally:
            override_settings(None)

    def test_draft_primitive_allowed_when_flag_set(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_full_ds(tmp_path, status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=True,
        ))
        try:
            result = generate_presentation(self._deck_yaml_with_top_level_primitive())
            assert result.governance_warnings == []
        finally:
            override_settings(None)

    def test_deprecated_primitive_emits_warning(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_full_ds(tmp_path, status="deprecated")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=False,
        ))
        try:
            result = generate_presentation(self._deck_yaml_with_top_level_primitive())
            assert len(result.governance_warnings) >= 1
            assert any("DEPRECATED" in w for w in result.governance_warnings)
        finally:
            override_settings(None)

    def test_approved_primitive_no_warnings(self, tmp_path):
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_full_ds(tmp_path, status="approved")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=False,
        ))
        try:
            result = generate_presentation(self._deck_yaml_with_top_level_primitive())
            assert result.governance_warnings == []
        finally:
            override_settings(None)

    def test_governance_warnings_is_empty_list_by_default(self):
        """PipelineResult.governance_warnings defaults to empty list."""
        from pptgen.pipeline.generation_pipeline import PipelineResult
        result = PipelineResult(
            stage="deck_planned",
            playbook_id="test",
            input_text="",
        )
        assert result.governance_warnings == []

    def test_no_warnings_when_no_governance_metadata(self):
        """Real design_system artifacts have no governance block → no warnings."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        deck_yaml = (
            "slides:\n"
            "  - primitive: title_slide\n"
            "    content:\n"
            "      title: Hello\n"
        )
        result = generate_presentation(deck_yaml)
        assert result.governance_warnings == []


# ---------------------------------------------------------------------------
# TestPerSlidePrimitiveGovernance — Phase 10C patch
# ---------------------------------------------------------------------------


class TestPerSlidePrimitiveGovernance:
    """Tests for _enforce_per_slide_primitive_governance() wired into the pipeline.

    Per-slide ``primitive:`` entries (inside ``slides:`` list) were previously
    invisible to governance. Phase 10C-P closes this gap. These tests exercise
    the patch in isolation from top-level ``primitive:`` resolution.
    """

    def _make_ds_with_slide_primitive(
        self,
        tmp_path: Path,
        status: str = "approved",
        primitive_id: str = "slide_prim",
    ) -> Path:
        """Minimal design_system with one primitive used per-slide only."""
        ds = tmp_path / "ds"
        (ds / "primitives").mkdir(parents=True)
        (ds / "primitives" / f"{primitive_id}.yaml").write_text(
            f"schema_version: 1\n"
            f"primitive_id: {primitive_id}\n"
            f"version: \"1.0.0\"\n"
            f"layout_id: single_column\n"
            f"constraints:\n  allow_extra_content: true\n"
            f"slots:\n"
            f"  title:\n"
            f"    required: false\n"
            f"    content_type: string\n"
            f"    maps_to: content\n"
            f"    description: \"Title\"\n"
            f"governance:\n  status: {status}\n",
            encoding="utf-8",
        )
        (ds / "layouts").mkdir(parents=True)
        (ds / "layouts" / "single_column.yaml").write_text(
            "schema_version: 1\n"
            "layout_id: single_column\n"
            "version: \"1.0.0\"\n"
            "regions:\n  content:\n    required: false\n    label: Main\n",
            encoding="utf-8",
        )
        (ds / "tokens").mkdir(parents=True)
        (ds / "tokens" / "base_tokens.yaml").write_text(
            "schema_version: 1\nversion: \"1.0.0\"\ntokens:\n  color.primary: \"#000\"\n",
            encoding="utf-8",
        )
        (ds / "brands").mkdir(parents=True)
        (ds / "brands" / "default.yaml").write_text(
            "schema_version: 1\nbrand_id: default\nversion: \"1.0.0\"\ntoken_overrides: {}\n",
            encoding="utf-8",
        )
        (ds / "themes").mkdir(parents=True)
        (ds / "themes" / "default.yaml").write_text(
            "schema_version: 1\ntheme_id: default\nversion: \"1.0.0\"\nbrand_id: default\n",
            encoding="utf-8",
        )
        (ds / "assets").mkdir(parents=True)
        return ds

    def _slides_only_deck(self, primitive_id: str = "slide_prim") -> str:
        """Deck with per-slide primitive but no top-level primitive: key."""
        return (
            f"slides:\n"
            f"  - primitive: {primitive_id}\n"
            f"    content:\n"
            f"      title: Slide 1\n"
        )

    def _slides_only_deck_multi(self, primitive_id: str = "slide_prim") -> str:
        """Same primitive used in two slides."""
        return (
            f"slides:\n"
            f"  - primitive: {primitive_id}\n"
            f"    content:\n"
            f"      title: Slide 1\n"
            f"  - primitive: {primitive_id}\n"
            f"    content:\n"
            f"      title: Slide 2\n"
        )

    def test_per_slide_draft_blocked_by_default(self, tmp_path):
        """DRAFT per-slide primitive raises PipelineError by default."""
        from pptgen.pipeline.generation_pipeline import PipelineError, generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=False,
        ))
        try:
            with pytest.raises(PipelineError, match="DRAFT"):
                generate_presentation(self._slides_only_deck())
        finally:
            override_settings(None)

    def test_per_slide_draft_allowed_when_flag_set(self, tmp_path):
        """DRAFT per-slide primitive is permitted when allow_draft_artifacts=True."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=True,
        ))
        try:
            result = generate_presentation(self._slides_only_deck())
            assert result.governance_warnings == []
        finally:
            override_settings(None)

    def test_per_slide_deprecated_emits_warning(self, tmp_path):
        """DEPRECATED per-slide primitive emits exactly one warning."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(self._slides_only_deck())
            dep_warnings = [w for w in result.governance_warnings if "DEPRECATED" in w]
            assert len(dep_warnings) == 1
            assert "slide_prim" in dep_warnings[0]
        finally:
            override_settings(None)

    def test_per_slide_deprecated_same_primitive_multi_slides_one_warning(self, tmp_path):
        """Same DEPRECATED primitive in two slides produces exactly one warning."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(self._slides_only_deck_multi())
            dep_warnings = [w for w in result.governance_warnings if "DEPRECATED" in w]
            assert len(dep_warnings) == 1
        finally:
            override_settings(None)

    def test_per_slide_deprecated_no_duplicate_warning_when_also_top_level(self, tmp_path):
        """When primitive appears at both top-level and per-slide, exactly one warning."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="deprecated")
        # Same primitive at top-level AND in slides
        deck_yaml = (
            "primitive: slide_prim\n"
            "content:\n  title: Main\n"
            "slides:\n"
            "  - primitive: slide_prim\n"
            "    content:\n      title: Slide 1\n"
        )
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(deck_yaml)
            dep_warnings = [w for w in result.governance_warnings if "DEPRECATED" in w]
            assert len(dep_warnings) == 1
        finally:
            override_settings(None)

    def test_per_slide_primitive_recorded_in_dependency_chain(self, tmp_path):
        """Per-slide primitive appears in dependency_chain."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="approved")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(self._slides_only_deck())
            prim_deps = [
                d for d in result.dependency_chain
                if d.artifact_type == "primitive" and d.artifact_id == "slide_prim"
            ]
            assert len(prim_deps) == 1
            assert prim_deps[0].version == "1.0.0"
            assert prim_deps[0].lifecycle_status == "approved"
        finally:
            override_settings(None)

    def test_per_slide_same_primitive_multi_slides_one_chain_entry(self, tmp_path):
        """Same primitive in two slides appears only once in dependency_chain."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="approved")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(self._slides_only_deck_multi())
            prim_deps = [
                d for d in result.dependency_chain
                if d.artifact_type == "primitive" and d.artifact_id == "slide_prim"
            ]
            assert len(prim_deps) == 1
        finally:
            override_settings(None)

    def test_unknown_per_slide_primitive_is_skipped_silently(self, tmp_path):
        """Unknown per-slide primitive ID does not crash the pipeline."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="approved")
        deck_yaml = (
            "slides:\n"
            "  - primitive: no_such_primitive_xyz\n"
            "    content:\n      title: Slide 1\n"
        )
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(deck_yaml)
            assert result.governance_warnings == []
            prim_deps = [d for d in result.dependency_chain if d.artifact_type == "primitive"]
            assert all(d.artifact_id != "no_such_primitive_xyz" for d in prim_deps)
        finally:
            override_settings(None)

    def test_approved_per_slide_primitive_no_warnings(self, tmp_path):
        """APPROVED per-slide primitive generates no warnings."""
        from pptgen.pipeline.generation_pipeline import generate_presentation

        ds = self._make_ds_with_slide_primitive(tmp_path, status="approved")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(self._slides_only_deck())
            assert result.governance_warnings == []
        finally:
            override_settings(None)
