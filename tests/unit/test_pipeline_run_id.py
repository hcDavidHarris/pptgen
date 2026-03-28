"""Unit tests for Phase 10D.2 — PipelineResult run_id and failure_attribution.

Covers:
PipelineResult model
- run_id defaults to empty string (backward-compatible direct construction)
- failure_attribution defaults to None
- explicit run_id is stored correctly
- explicit failure_attribution is stored correctly
- existing construction (all pre-10D fields only) still works

generate_presentation() — run_id population
- result.run_id is a non-empty string
- result.run_id is a valid UUID (36 characters, hex + dashes)
- two separate calls produce different run_ids
- result.failure_attribution is None on a successful run

generate_presentation() — failure_attribution capture (observable via PipelineError)
- primitive stage failure raises PipelineError (attribution captured before re-raise)
- layout stage failure raises PipelineError
- theme stage failure raises PipelineError

Note: _failure_attribution is a local variable in generate_presentation() that is
populated inside except blocks before re-raising.  It is not yet consumed (that is
Phase 10D.3 — RunRecord emission).  Tests here verify the pre-raise exception is
still a PipelineError, and that the run_id on the SUCCESS path is correctly formed.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

from pptgen.analytics import FailureAttribution
from pptgen.config import RuntimeSettings, override_settings
from pptgen.pipeline.generation_pipeline import PipelineError, PipelineResult, generate_presentation


# ---------------------------------------------------------------------------
# Minimal design-system fixture (reuses the _make_ds pattern from 10C tests)
# ---------------------------------------------------------------------------

def _make_ds(
    tmp: Path,
    primitive_status: str = "approved",
    layout_status: str = "approved",
    theme_status: str = "approved",
) -> Path:
    """Minimal design_system matching the schema expected by the registry."""
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

    (ds / "themes" / "executive.yaml").write_text(textwrap.dedent(f"""\
        schema_version: 1
        theme_id: executive
        version: "1.0.0"
        brand_id: default
        governance:
          status: {theme_status}
    """), encoding="utf-8")

    return ds


_PRIM_DECK = textwrap.dedent("""\
    primitive: title_slide
    content:
      title: Hello World
    slides:
      - primitive: title_slide
        content:
          title: Slide 1
""")

_LAYOUT_DECK = textwrap.dedent("""\
    layout: single_column
    slots:
      content: Hello
    slides:
      - type: title
        title: Test
""")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


# ---------------------------------------------------------------------------
# PipelineResult model — unit tests (no pipeline invocation)
# ---------------------------------------------------------------------------


class TestPipelineResultDefaults:
    def test_run_id_defaults_to_empty_string(self):
        result = PipelineResult(stage="deck_planned", playbook_id="x", input_text="")
        assert result.run_id == ""

    def test_failure_attribution_defaults_to_none(self):
        result = PipelineResult(stage="deck_planned", playbook_id="x", input_text="")
        assert result.failure_attribution is None

    def test_explicit_run_id_stored(self):
        result = PipelineResult(
            stage="deck_planned", playbook_id="x", input_text="",
            run_id="abc-123",
        )
        assert result.run_id == "abc-123"

    def test_explicit_failure_attribution_stored(self):
        fa = FailureAttribution(
            stage="layout",
            artifact_type="layout",
            artifact_id="executive",
            error_type="GovernanceViolationError",
        )
        result = PipelineResult(
            stage="deck_planned", playbook_id="x", input_text="",
            failure_attribution=fa,
        )
        assert result.failure_attribution is fa

    def test_backward_compatible_construction_without_new_fields(self):
        """Existing callers that don't pass run_id / failure_attribution still work."""
        result = PipelineResult(
            stage="rendered",
            playbook_id="exec",
            input_text="hello",
            mode="deterministic",
        )
        assert result.run_id == ""
        assert result.failure_attribution is None


# ---------------------------------------------------------------------------
# generate_presentation() — run_id population
# ---------------------------------------------------------------------------


class TestRunIdPopulation:
    def test_run_id_is_non_empty(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.run_id != ""

    def test_run_id_is_valid_uuid4(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert _UUID_RE.match(result.run_id), (
            f"run_id {result.run_id!r} is not a valid UUID4"
        )

    def test_two_calls_produce_different_run_ids(self):
        r1 = generate_presentation("prepare an executive summary for Q3 results")
        r2 = generate_presentation("prepare an executive summary for Q3 results")
        assert r1.run_id != r2.run_id

    def test_run_id_present_on_deck_planned_stage(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.stage == "deck_planned"
        assert result.run_id != ""

    def test_run_id_present_when_design_system_used(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert _UUID_RE.match(result.run_id)

    def test_failure_attribution_is_none_on_success(self):
        result = generate_presentation("prepare an executive summary for Q3 results")
        assert result.failure_attribution is None

    def test_failure_attribution_is_none_with_design_system(self, tmp_path):
        ds = _make_ds(tmp_path)
        override_settings(RuntimeSettings(design_system_path=str(ds)))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert result.failure_attribution is None


# ---------------------------------------------------------------------------
# generate_presentation() — attribution capture (pre-raise side-effect)
# The _failure_attribution local is populated before re-raise.
# These tests confirm the error surfaces as PipelineError (not the raw
# DesignSystemError) — i.e. the attribution capture doesn't suppress re-raise.
# ---------------------------------------------------------------------------


class TestAttributionCaptureDoesNotSuppressRaise:
    """Verify that adding attribution capture before re-raise doesn't change
    the exception type or message surfaced to callers."""

    def test_draft_primitive_still_raises_pipeline_error(self, tmp_path):
        ds = _make_ds(tmp_path, primitive_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=False,
        ))
        try:
            with pytest.raises(PipelineError):
                generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)

    def test_draft_layout_still_raises_pipeline_error(self, tmp_path):
        ds = _make_ds(tmp_path, layout_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=False,
        ))
        try:
            with pytest.raises(PipelineError):
                generate_presentation(_LAYOUT_DECK)
        finally:
            override_settings(None)

    def test_draft_theme_still_raises_pipeline_error(self, tmp_path):
        ds = _make_ds(tmp_path, theme_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            default_theme="executive",
            allow_draft_artifacts=False,
        ))
        try:
            with pytest.raises(PipelineError):
                generate_presentation("prepare an executive summary")
        finally:
            override_settings(None)

    def test_draft_with_override_succeeds_with_run_id(self, tmp_path):
        """When draft is allowed, attribution is NOT captured — run succeeds."""
        ds = _make_ds(tmp_path, primitive_status="draft")
        override_settings(RuntimeSettings(
            design_system_path=str(ds),
            allow_draft_artifacts=True,
        ))
        try:
            result = generate_presentation(_PRIM_DECK)
        finally:
            override_settings(None)
        assert _UUID_RE.match(result.run_id)
        assert result.failure_attribution is None
