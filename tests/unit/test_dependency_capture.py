"""Unit tests for Phase 10C — runtime dependency capture.

Covers:
- primitive resolution records a primitive dependency
- layout resolution records a layout dependency
- theme resolution records a theme dependency
- token_set resolution records a token_set dependency
- asset resolution records an asset dependency
- deprecated dependency is recorded with lifecycle_status='deprecated'
- draft dependency is blocked consistently with Phase 10B enforcement
- draft dependency succeeds when allow_draft_artifacts=True
- same asset referenced twice → exactly one chain entry (dedup)
- ordering is deterministic: primitive → layout → token_set → theme → asset(s)
- dependency_chain is empty when no design-system keys are used
- PipelineResult.dependency_chain defaults to an empty list
- snapshot file written when artifacts_dir is provided
- snapshot omitted when dependency_chain is empty
- existing generation behavior is unchanged
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from pptgen.config import RuntimeSettings, override_settings
from pptgen.design_system.dependency_models import ResolvedArtifactDependency, record_dependency
from pptgen.pipeline.generation_pipeline import PipelineError, PipelineResult, generate_presentation


DESIGN_SYSTEM_PATH = Path("design_system")


# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------


def _make_ds(
    tmp: Path,
    primitive_status: str = "approved",
    layout_status: str = "approved",
    theme_status: str = "approved",
    asset_status: str = "approved",
) -> Path:
    """Create a minimal design_system with configurable governance statuses."""
    ds = tmp / "ds"
    for subdir in ("primitives", "layouts", "tokens", "brands", "themes", "assets"):
        (ds / subdir).mkdir(parents=True)

    (ds / "primitives" / "title_slide.yaml").write_text(textwrap.dedent(f"""\
        schema_version: 1
        primitive_id: title_slide
        version: "1.0.0"
        layout_id: single_column
        constraints:
          allow_extra_content: true
        slots:
          title:
            required: false
            content_type: string
            maps_to: content
            description: Title
        governance:
          status: {primitive_status}
    """), encoding="utf-8")

    (ds / "layouts" / "single_column.yaml").write_text(textwrap.dedent(f"""\
        schema_version: 1
        layout_id: single_column
        version: "1.0.0"
        regions:
          content:
            required: false
            label: Main content
        governance:
          status: {layout_status}
    """), encoding="utf-8")

    (ds / "tokens" / "base_tokens.yaml").write_text(textwrap.dedent("""\
        schema_version: 1
        version: "1.0.0"
        tokens:
          color.primary: "#000000"
    """), encoding="utf-8")

    (ds / "brands" / "default.yaml").write_text(textwrap.dedent("""\
        schema_version: 1
        brand_id: default
        version: "1.0.0"
        token_overrides: {}
    """), encoding="utf-8")

    (ds / "themes" / "default.yaml").write_text(textwrap.dedent(f"""\
        schema_version: 1
        theme_id: default
        version: "1.0.0"
        brand_id: default
        governance:
          status: {theme_status}
    """), encoding="utf-8")

    (ds / "assets" / "icon.check.yaml").write_text(textwrap.dedent(f"""\
        schema_version: 1
        asset_id: icon.check
        version: "1.0.0"
        type: icon
        source: assets/icons/check.svg
        governance:
          status: {asset_status}
    """), encoding="utf-8")

    return ds


# Deck YAML with a top-level primitive — triggers primitive + layout resolution.
_PRIM_DECK = textwrap.dedent("""\
    primitive: title_slide
    content:
      title: Hello
    slides:
      - primitive: title_slide
        content:
          title: Slide 1
""")

# Deck with a top-level layout — triggers layout resolution only.
_LAYOUT_DECK = textwrap.dedent("""\
    layout: single_column
    slots:
      content: Hello
    slides:
      - type: title
        title: Test
""")

# Plain structured deck — no design-system keys at all.
_PLAIN_DECK = textwrap.dedent("""\
    slides:
      - type: title
        title: Test
""")

# Deck with an asset reference.
_ASSET_DECK = textwrap.dedent("""\
    slides:
      - type: title
        title: Test
        icon:
          asset_id: icon.check
""")

# Deck with the same asset referenced twice.
_DUPLICATE_ASSET_DECK = textwrap.dedent("""\
    slides:
      - type: title
        title: Slide 1
        icon:
          asset_id: icon.check
      - type: title
        title: Slide 2
        icon:
          asset_id: icon.check
""")

# Full deck — triggers all five artifact types when default_theme is set.
_FULL_DECK = textwrap.dedent("""\
    primitive: title_slide
    content:
      title: Hello
    slides:
      - primitive: title_slide
        content:
          title: Slide 1
          icon:
            asset_id: icon.check
""")


# ---------------------------------------------------------------------------
# TestRecordDependencyHelper — unit tests for the shared helper directly
# ---------------------------------------------------------------------------


class TestRecordDependencyHelper:
    def test_appends_record(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "primitive", "bullet_slide", "1.0.0", "approved", "primitive")
        assert len(chain) == 1
        assert chain[0].artifact_type == "primitive"
        assert chain[0].artifact_id == "bullet_slide"
        assert chain[0].version == "1.0.0"
        assert chain[0].lifecycle_status == "approved"
        assert chain[0].source == "primitive"

    def test_dedup_same_key(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "asset", "icon.check", "1.0.0", "approved", "asset")
        record_dependency(chain, "asset", "icon.check", "1.0.0", "approved", "asset")
        assert len(chain) == 1

    def test_different_version_is_separate_record(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "primitive", "x", "1.0.0", "approved", "primitive")
        record_dependency(chain, "primitive", "x", "2.0.0", "approved", "primitive")
        assert len(chain) == 2

    def test_none_version_accepted(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "asset", "x", None, None, "asset")
        assert chain[0].version is None
        assert chain[0].lifecycle_status is None

    def test_none_version_deduplicates(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "asset", "x", None, None, "asset")
        record_dependency(chain, "asset", "x", None, None, "asset")
        assert len(chain) == 1

    def test_insertion_order_preserved(self):
        chain: list[ResolvedArtifactDependency] = []
        for t in ("primitive", "layout", "token_set", "theme", "asset"):
            record_dependency(chain, t, t, "1.0.0", "approved", t)
        assert [d.artifact_type for d in chain] == [
            "primitive", "layout", "token_set", "theme", "asset"
        ]

    def test_result_is_frozen(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "layout", "x", "1.0.0", "approved", "layout")
        with pytest.raises((AttributeError, TypeError)):
            chain[0].artifact_id = "mutated"  # type: ignore[misc]

    def test_to_dict_all_keys_present(self):
        chain: list[ResolvedArtifactDependency] = []
        record_dependency(chain, "theme", "executive", "1.0.0", "deprecated", "theme")
        d = chain[0].to_dict()
        assert set(d.keys()) == {
            "artifact_type", "artifact_id", "version", "lifecycle_status", "source"
        }


# ---------------------------------------------------------------------------
# TestPrimitiveDependencyCapture
# ---------------------------------------------------------------------------


class TestPrimitiveDependencyCapture:
    def test_primitive_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim_deps = [d for d in result.dependency_chain if d.artifact_type == "primitive"]
        assert len(prim_deps) == 1

    def test_primitive_artifact_id(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.artifact_id == "title_slide"

    def test_primitive_version(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.version == "1.0.0"

    def test_primitive_lifecycle_status(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.lifecycle_status == "approved"

    def test_primitive_source_field(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.source == "primitive"

    def test_no_primitive_when_not_declared(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        prim_deps = [d for d in result.dependency_chain if d.artifact_type == "primitive"]
        assert prim_deps == []


# ---------------------------------------------------------------------------
# TestLayoutDependencyCapture
# ---------------------------------------------------------------------------


class TestLayoutDependencyCapture:
    def test_layout_in_chain_from_primitive(self, tmp_path):
        """Layout injected by primitive resolution is captured."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        layout_deps = [d for d in result.dependency_chain if d.artifact_type == "layout"]
        assert len(layout_deps) == 1

    def test_layout_in_chain_from_direct_declaration(self, tmp_path):
        """Layout declared directly at deck level is captured."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

        layout_deps = [d for d in result.dependency_chain if d.artifact_type == "layout"]
        assert len(layout_deps) == 1

    def test_layout_artifact_id(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

        layout = next(d for d in result.dependency_chain if d.artifact_type == "layout")
        assert layout.artifact_id == "single_column"

    def test_layout_version(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

        layout = next(d for d in result.dependency_chain if d.artifact_type == "layout")
        assert layout.version == "1.0.0"

    def test_layout_lifecycle_status(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

        layout = next(d for d in result.dependency_chain if d.artifact_type == "layout")
        assert layout.lifecycle_status == "approved"


# ---------------------------------------------------------------------------
# TestThemeTokenDependencyCapture
# ---------------------------------------------------------------------------


class TestThemeTokenDependencyCapture:
    def test_theme_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        theme_deps = [d for d in result.dependency_chain if d.artifact_type == "theme"]
        assert len(theme_deps) == 1

    def test_token_set_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        token_deps = [d for d in result.dependency_chain if d.artifact_type == "token_set"]
        assert len(token_deps) == 1

    def test_theme_artifact_id(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        theme = next(d for d in result.dependency_chain if d.artifact_type == "theme")
        assert theme.artifact_id == "default"

    def test_token_set_artifact_id_is_base(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        token = next(d for d in result.dependency_chain if d.artifact_type == "token_set")
        assert token.artifact_id == "base"

    def test_token_set_before_theme_in_chain(self, tmp_path):
        """token_set is resolved (and captured) before theme within the same stage."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        types = [d.artifact_type for d in result.dependency_chain]
        assert types.index("token_set") < types.index("theme")

    def test_no_theme_when_not_configured(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds), default_theme=""))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        theme_deps = [d for d in result.dependency_chain if d.artifact_type == "theme"]
        assert theme_deps == []


# ---------------------------------------------------------------------------
# TestAssetDependencyCapture
# ---------------------------------------------------------------------------


class TestAssetDependencyCapture:
    def test_asset_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset_deps = [d for d in result.dependency_chain if d.artifact_type == "asset"]
        assert len(asset_deps) == 1

    def test_asset_artifact_id(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset = next(d for d in result.dependency_chain if d.artifact_type == "asset")
        assert asset.artifact_id == "icon.check"

    def test_asset_version(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset = next(d for d in result.dependency_chain if d.artifact_type == "asset")
        assert asset.version == "1.0.0"

    def test_asset_lifecycle_status(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset = next(d for d in result.dependency_chain if d.artifact_type == "asset")
        assert asset.lifecycle_status == "approved"

    def test_asset_source_field(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset = next(d for d in result.dependency_chain if d.artifact_type == "asset")
        assert asset.source == "asset"


# ---------------------------------------------------------------------------
# TestDeprecatedDependencyCapture
# ---------------------------------------------------------------------------


class TestDeprecatedDependencyCapture:
    def test_deprecated_primitive_lifecycle_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path, primitive_status="deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.lifecycle_status == "deprecated"

    def test_deprecated_layout_lifecycle_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path, layout_status="deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

        layout = next(d for d in result.dependency_chain if d.artifact_type == "layout")
        assert layout.lifecycle_status == "deprecated"

    def test_deprecated_theme_lifecycle_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path, theme_status="deprecated")
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        theme = next(d for d in result.dependency_chain if d.artifact_type == "theme")
        assert theme.lifecycle_status == "deprecated"

    def test_deprecated_asset_lifecycle_in_chain(self, tmp_path):
        ds = _make_ds(tmp_path, asset_status="deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset = next(d for d in result.dependency_chain if d.artifact_type == "asset")
        assert asset.lifecycle_status == "deprecated"

    def test_deprecated_chain_entry_and_warning_agree(self, tmp_path):
        """Deprecated primitive appears in both chain and governance_warnings."""
        ds = _make_ds(tmp_path, primitive_status="deprecated")
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.lifecycle_status == "deprecated"
        assert any("DEPRECATED" in w and "title_slide" in w
                   for w in result.governance_warnings)

    def test_approved_artifacts_have_no_warnings(self, tmp_path):
        ds = _make_ds(tmp_path)  # all approved
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        assert result.governance_warnings == []
        assert all(d.lifecycle_status == "approved" for d in result.dependency_chain)


# ---------------------------------------------------------------------------
# TestDraftDependencyEnforcement
# ---------------------------------------------------------------------------


class TestDraftDependencyEnforcement:
    def test_draft_primitive_blocked_by_default(self, tmp_path):
        ds = _make_ds(tmp_path, primitive_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds), allow_draft_artifacts=False
        ))
        try:
            with pytest.raises(PipelineError, match="DRAFT"):
                generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

    def test_draft_layout_blocked_by_default(self, tmp_path):
        ds = _make_ds(tmp_path, layout_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds), allow_draft_artifacts=False
        ))
        try:
            with pytest.raises(PipelineError, match="DRAFT"):
                generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

    def test_draft_asset_blocked_by_default(self, tmp_path):
        ds = _make_ds(tmp_path, asset_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds), allow_draft_artifacts=False
        ))
        try:
            with pytest.raises(PipelineError, match="DRAFT"):
                generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

    def test_draft_primitive_allowed_with_override(self, tmp_path):
        ds = _make_ds(tmp_path, primitive_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds), allow_draft_artifacts=True
        ))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim = next(d for d in result.dependency_chain if d.artifact_type == "primitive")
        assert prim.lifecycle_status == "draft"
        assert result.governance_warnings == []

    def test_draft_asset_allowed_with_override(self, tmp_path):
        ds = _make_ds(tmp_path, asset_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds), allow_draft_artifacts=True
        ))
        try:
            result = generate_presentation(_ASSET_DECK)
        finally:
            override_settings(None)

        asset = next(d for d in result.dependency_chain if d.artifact_type == "asset")
        assert asset.lifecycle_status == "draft"


# ---------------------------------------------------------------------------
# TestDependencyDeduplication
# ---------------------------------------------------------------------------


class TestDependencyDeduplication:
    def test_same_asset_twice_one_chain_entry(self, tmp_path):
        """Same asset_id referenced in two slides → exactly one dependency record."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_DUPLICATE_ASSET_DECK)
        finally:
            override_settings(None)

        asset_deps = [d for d in result.dependency_chain if d.artifact_type == "asset"]
        assert len(asset_deps) == 1
        assert asset_deps[0].artifact_id == "icon.check"

    def test_primitive_recorded_once_even_with_slides_primitives(self, tmp_path):
        """Top-level primitive resolved once; per-slide primitives do not add duplicates."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        prim_deps = [d for d in result.dependency_chain if d.artifact_type == "primitive"]
        assert len(prim_deps) == 1


# ---------------------------------------------------------------------------
# TestDependencyOrdering
# ---------------------------------------------------------------------------


class TestDependencyOrdering:
    def test_full_ordering_primitive_layout_tokenset_theme_asset(self, tmp_path):
        """Resolution order: primitive → layout → token_set → theme → asset."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            result = generate_presentation(_FULL_DECK)
        finally:
            override_settings(None)

        types = [d.artifact_type for d in result.dependency_chain]
        assert types == ["primitive", "layout", "token_set", "theme", "asset"]

    def test_ordering_is_stable_across_calls(self, tmp_path):
        """Same input produces the same chain order on repeated calls."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds), default_theme="default"
        ))
        try:
            r1 = generate_presentation(_FULL_DECK)
            r2 = generate_presentation(_FULL_DECK)
        finally:
            override_settings(None)

        ids1 = [(d.artifact_type, d.artifact_id) for d in r1.dependency_chain]
        ids2 = [(d.artifact_type, d.artifact_id) for d in r2.dependency_chain]
        assert ids1 == ids2

    def test_asset_ordering_by_first_occurrence(self, tmp_path):
        """Multiple distinct assets appear in first-encountered order."""
        ds = _make_ds(tmp_path)
        # Add a second asset
        (ds / "assets" / "icon.warning.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            asset_id: icon.warning
            version: "1.0.0"
            type: icon
            source: assets/icons/warning.svg
            governance:
              status: approved
        """), encoding="utf-8")

        deck = textwrap.dedent("""\
            slides:
              - type: title
                title: Slide 1
                a: {asset_id: icon.check}
              - type: title
                title: Slide 2
                b: {asset_id: icon.warning}
        """)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(deck)
        finally:
            override_settings(None)

        asset_ids = [d.artifact_id for d in result.dependency_chain
                     if d.artifact_type == "asset"]
        assert asset_ids == ["icon.check", "icon.warning"]


# ---------------------------------------------------------------------------
# TestSnapshotSurface
# ---------------------------------------------------------------------------


class TestSnapshotSurface:
    def test_snapshot_written_when_artifacts_dir_provided(self, tmp_path):
        ds = _make_ds(tmp_path)
        art = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK, artifacts_dir=art)
        finally:
            override_settings(None)

        snap_path = art / "resolved_dependencies_snapshot.json"
        assert snap_path.exists()

    def test_snapshot_key_in_artifact_paths(self, tmp_path):
        ds = _make_ds(tmp_path)
        art = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK, artifacts_dir=art)
        finally:
            override_settings(None)

        assert "resolved_dependencies_snapshot" in result.artifact_paths

    def test_snapshot_shape(self, tmp_path):
        ds = _make_ds(tmp_path)
        art = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            generate_presentation(_PRIM_DECK, artifacts_dir=art)
        finally:
            override_settings(None)

        snap = json.loads((art / "resolved_dependencies_snapshot.json").read_text())
        assert "dependencies" in snap
        for entry in snap["dependencies"]:
            assert set(entry.keys()) == {
                "artifact_type", "artifact_id", "version", "lifecycle_status", "source"
            }

    def test_snapshot_order_matches_chain(self, tmp_path):
        ds = _make_ds(tmp_path)
        art = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK, artifacts_dir=art)
        finally:
            override_settings(None)

        snap = json.loads((art / "resolved_dependencies_snapshot.json").read_text())
        chain_ids = [d.artifact_id for d in result.dependency_chain]
        snap_ids  = [e["artifact_id"] for e in snap["dependencies"]]
        assert chain_ids == snap_ids

    def test_snapshot_omitted_when_chain_empty(self, tmp_path):
        ds = _make_ds(tmp_path)
        art = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PLAIN_DECK, artifacts_dir=art)
        finally:
            override_settings(None)

        assert result.dependency_chain == []
        assert not (art / "resolved_dependencies_snapshot.json").exists()
        assert "resolved_dependencies_snapshot" not in (result.artifact_paths or {})


# ---------------------------------------------------------------------------
# TestExistingBehaviorUnchanged — regression guards
# ---------------------------------------------------------------------------


class TestExistingBehaviorUnchanged:
    def test_pipeline_result_defaults(self):
        result = PipelineResult(stage="deck_planned", playbook_id="x", input_text="")
        assert result.dependency_chain == []
        assert result.governance_warnings == []

    def test_plain_deck_has_empty_chain(self, tmp_path):
        """No design-system keys → empty dependency_chain."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PLAIN_DECK)
        finally:
            override_settings(None)

        assert result.dependency_chain == []

    def test_real_ds_primitive_deck_resolves(self):
        """Real design_system/ primitives still resolve correctly."""
        deck = textwrap.dedent("""\
            slides:
              - primitive: bullet_slide
                content:
                  title: Test
                  bullets:
                    - point one
                    - point two
        """)
        result = generate_presentation(deck)
        assert result.stage == "deck_planned"

    def test_real_ds_dependency_chain_entries_have_stable_shape(self):
        """Real design_system assets produce dependency records with correct keys."""
        deck = textwrap.dedent("""\
            slides:
              - type: title
                title: Test
                icon:
                  asset_id: icon.check
        """)
        result = generate_presentation(deck)
        asset_deps = [d for d in result.dependency_chain if d.artifact_type == "asset"]
        assert len(asset_deps) == 1
        d = asset_deps[0]
        assert d.artifact_id == "icon.check"
        assert d.source == "asset"
        assert d.version is not None

    def test_dependency_chain_does_not_affect_deck_definition(self, tmp_path):
        """Dependency capture must not mutate or corrupt deck_definition."""
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

        assert isinstance(result.deck_definition, dict)
        assert "slides" in result.deck_definition
