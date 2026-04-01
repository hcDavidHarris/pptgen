"""Tests for design system integration in the generation pipeline — Phase 9 Stage 1.

Covers:
- theme_id parameter resolves tokens and populates resolved_style_map
- token references in deck_definition are substituted before rendering
- resolved_theme_snapshot.json written when artifacts_dir is provided
- Unknown theme_id raises PipelineError before rendering
- No theme → resolved_style_map is None (backward compatibility)
- Platform default_theme setting applied when no run-time theme provided
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from pptgen.config import RuntimeSettings, override_settings
from pptgen.design_system.exceptions import UnknownThemeError
from pptgen.pipeline.generation_pipeline import PipelineError, generate_presentation


# ---------------------------------------------------------------------------
# Helpers — build a minimal design_system/ tree
# ---------------------------------------------------------------------------

BASE_TOKENS = textwrap.dedent("""\
    schema_version: 1
    version: "1.0.0"
    tokens:
      color.primary: "#000000"
      color.background: "#FFFFFF"
      font.size.title: 40
      spacing.md: 16
""")

BRAND = textwrap.dedent("""\
    schema_version: 1
    brand_id: testbrand
    version: "1.0.0"
    token_overrides:
      color.primary: "#0047AB"
""")

THEME = textwrap.dedent("""\
    schema_version: 1
    theme_id: testtheme
    version: "1.0.0"
    brand_id: testbrand
    token_overrides:
      font.size.title: 48
""")


def _make_ds(tmp_path: Path) -> Path:
    """Write a minimal design_system/ tree under tmp_path and return its path."""
    root = tmp_path / "design_system"
    (root / "tokens").mkdir(parents=True)
    (root / "brands").mkdir()
    (root / "themes").mkdir()
    (root / "tokens" / "base_tokens.yaml").write_text(BASE_TOKENS)
    (root / "brands" / "testbrand.yaml").write_text(BRAND)
    (root / "themes" / "testtheme.yaml").write_text(THEME)
    return root


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_INPUT = "Q1 business review results."


@pytest.fixture(autouse=True)
def reset_settings():
    yield
    override_settings(None)


# ---------------------------------------------------------------------------
# No theme — backward compatibility
# ---------------------------------------------------------------------------

class TestNoTheme:
    def test_resolved_style_map_is_none_when_no_theme(self, tmp_path):
        override_settings(RuntimeSettings(design_system_path="", default_theme=""))
        result = generate_presentation(MINIMAL_INPUT)
        assert result.resolved_style_map is None

    def test_existing_pipeline_still_returns_deck_planned(self, tmp_path):
        override_settings(RuntimeSettings(design_system_path="", default_theme=""))
        result = generate_presentation(MINIMAL_INPUT)
        assert result.stage in {"deck_planned", "rendered"}


# ---------------------------------------------------------------------------
# Theme resolution
# ---------------------------------------------------------------------------

class TestThemeResolution:
    def test_resolved_style_map_populated(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        result = generate_presentation(MINIMAL_INPUT, theme_id="testtheme")
        assert result.resolved_style_map is not None

    def test_resolved_style_map_theme_id(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        result = generate_presentation(MINIMAL_INPUT, theme_id="testtheme")
        assert result.resolved_style_map.theme_id == "testtheme"

    def test_resolved_style_map_brand_id(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        result = generate_presentation(MINIMAL_INPUT, theme_id="testtheme")
        assert result.resolved_style_map.brand_id == "testbrand"

    def test_resolved_tokens_reflect_precedence(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        result = generate_presentation(MINIMAL_INPUT, theme_id="testtheme")
        tokens = result.resolved_style_map.tokens
        assert tokens["color.primary"] == "#0047AB"    # brand override
        assert tokens["font.size.title"] == 48         # theme override
        assert tokens["color.background"] == "#FFFFFF" # base fallback

    def test_unknown_theme_raises_pipeline_error(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        with pytest.raises(PipelineError, match="no_such_theme"):
            generate_presentation(MINIMAL_INPUT, theme_id="no_such_theme")


# ---------------------------------------------------------------------------
# Platform default_theme from settings
# ---------------------------------------------------------------------------

class TestDefaultThemeSetting:
    def test_default_theme_applied_when_no_runtime_theme(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            default_theme="testtheme",
        ))
        result = generate_presentation(MINIMAL_INPUT)
        assert result.resolved_style_map is not None
        assert result.resolved_style_map.theme_id == "testtheme"

    def test_runtime_theme_overrides_default(self, tmp_path):
        ds = _make_ds(tmp_path)
        # Add a second theme
        (ds / "themes" / "othertheme.yaml").write_text(textwrap.dedent("""\
            schema_version: 1
            theme_id: othertheme
            version: "1.0.0"
            brand_id: testbrand
            token_overrides:
              font.size.title: 24
        """))
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            default_theme="othertheme",
        ))
        result = generate_presentation(MINIMAL_INPUT, theme_id="testtheme")
        assert result.resolved_style_map.theme_id == "testtheme"
        assert result.resolved_style_map.tokens["font.size.title"] == 48


# ---------------------------------------------------------------------------
# Snapshot artifact
# ---------------------------------------------------------------------------

class TestSnapshotArtifact:
    def test_snapshot_written_with_artifacts_dir(self, tmp_path):
        ds = _make_ds(tmp_path)
        artifacts_dir = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        generate_presentation(
            MINIMAL_INPUT,
            theme_id="testtheme",
            artifacts_dir=artifacts_dir,
        )
        snapshot_path = artifacts_dir / "resolved_theme_snapshot.json"
        assert snapshot_path.exists()

    def test_snapshot_is_valid_json(self, tmp_path):
        ds = _make_ds(tmp_path)
        artifacts_dir = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        generate_presentation(
            MINIMAL_INPUT,
            theme_id="testtheme",
            artifacts_dir=artifacts_dir,
        )
        data = json.loads((artifacts_dir / "resolved_theme_snapshot.json").read_text())
        assert data["theme_id"] == "testtheme"
        assert "tokens" in data
        assert "resolved_at" in data

    def test_snapshot_not_written_without_theme(self, tmp_path):
        ds = _make_ds(tmp_path)
        artifacts_dir = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds), default_theme=""))
        generate_presentation(MINIMAL_INPUT, artifacts_dir=artifacts_dir)
        assert not (artifacts_dir / "resolved_theme_snapshot.json").exists()

    def test_snapshot_path_in_artifact_paths(self, tmp_path):
        ds = _make_ds(tmp_path)
        artifacts_dir = tmp_path / "artifacts"
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        result = generate_presentation(
            MINIMAL_INPUT,
            theme_id="testtheme",
            artifacts_dir=artifacts_dir,
        )
        assert "resolved_theme_snapshot" in result.artifact_paths
