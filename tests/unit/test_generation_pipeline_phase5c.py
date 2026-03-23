"""Phase 5C pipeline tests — artifact export integration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptgen.pipeline import PipelineError, PipelineResult, generate_presentation


_TEXT = "Sprint 12 backlog velocity notes action items decisions."
_MEETING = "Meeting notes. Attendees: Alice, Bob. Action items: review deliverables."


# ---------------------------------------------------------------------------
# artifact_paths field on PipelineResult
# ---------------------------------------------------------------------------

class TestArtifactPathsField:
    def test_artifact_paths_none_by_default(self):
        result = generate_presentation(_TEXT)
        assert result.artifact_paths is None

    def test_artifact_paths_populated_when_dir_given(self, tmp_path):
        result = generate_presentation(_TEXT, artifacts_dir=tmp_path / "arts")
        assert result.artifact_paths is not None

    def test_artifact_paths_contains_three_keys(self, tmp_path):
        result = generate_presentation(_TEXT, artifacts_dir=tmp_path / "arts")
        assert set(result.artifact_paths.keys()) == {"spec", "slide_plan", "deck_definition"}

    def test_artifact_paths_values_are_strings(self, tmp_path):
        result = generate_presentation(_TEXT, artifacts_dir=tmp_path / "arts")
        for v in result.artifact_paths.values():
            assert isinstance(v, str)

    def test_artifact_paths_files_exist(self, tmp_path):
        result = generate_presentation(_TEXT, artifacts_dir=tmp_path / "arts")
        for path_str in result.artifact_paths.values():
            assert Path(path_str).exists()


# ---------------------------------------------------------------------------
# Artifacts written in deterministic mode
# ---------------------------------------------------------------------------

class TestArtifactsDeterministicMode:
    def test_spec_json_written(self, tmp_path):
        generate_presentation(_TEXT, artifacts_dir=tmp_path)
        assert (tmp_path / "spec.json").exists()

    def test_slide_plan_json_written(self, tmp_path):
        generate_presentation(_TEXT, artifacts_dir=tmp_path)
        assert (tmp_path / "slide_plan.json").exists()

    def test_deck_definition_json_written(self, tmp_path):
        generate_presentation(_TEXT, artifacts_dir=tmp_path)
        assert (tmp_path / "deck_definition.json").exists()

    def test_spec_json_is_valid(self, tmp_path):
        generate_presentation(_TEXT, artifacts_dir=tmp_path)
        data = json.loads((tmp_path / "spec.json").read_text(encoding="utf-8"))
        assert "title" in data

    def test_stage_is_deck_planned_without_output(self, tmp_path):
        result = generate_presentation(_TEXT, artifacts_dir=tmp_path)
        assert result.stage == "deck_planned"


# ---------------------------------------------------------------------------
# Artifacts written in AI mode
# ---------------------------------------------------------------------------

class TestArtifactsAIMode:
    def test_spec_json_written_ai(self, tmp_path):
        generate_presentation(_MEETING, artifacts_dir=tmp_path, mode="ai")
        assert (tmp_path / "spec.json").exists()

    def test_slide_plan_json_written_ai(self, tmp_path):
        generate_presentation(_MEETING, artifacts_dir=tmp_path, mode="ai")
        assert (tmp_path / "slide_plan.json").exists()

    def test_deck_definition_json_written_ai(self, tmp_path):
        generate_presentation(_MEETING, artifacts_dir=tmp_path, mode="ai")
        assert (tmp_path / "deck_definition.json").exists()

    def test_artifact_paths_populated_ai(self, tmp_path):
        result = generate_presentation(_MEETING, artifacts_dir=tmp_path, mode="ai")
        assert result.artifact_paths is not None
        assert len(result.artifact_paths) == 3


# ---------------------------------------------------------------------------
# Artifacts + output_path combined
# ---------------------------------------------------------------------------

class TestArtifactsWithOutput:
    def test_pptx_and_artifacts_both_written(self, tmp_path):
        out = tmp_path / "deck.pptx"
        arts = tmp_path / "arts"
        result = generate_presentation(_TEXT, output_path=out, artifacts_dir=arts)
        assert result.stage == "rendered"
        assert out.exists()
        assert (arts / "spec.json").exists()
        assert (arts / "slide_plan.json").exists()
        assert (arts / "deck_definition.json").exists()

    def test_output_path_populated(self, tmp_path):
        out = tmp_path / "deck.pptx"
        result = generate_presentation(_TEXT, output_path=out, artifacts_dir=tmp_path / "arts")
        assert result.output_path is not None
        assert result.output_path.endswith(".pptx")


# ---------------------------------------------------------------------------
# No artifacts when not requested
# ---------------------------------------------------------------------------

class TestNoArtifactsWhenNotRequested:
    def test_no_artifact_files_when_dir_is_none(self, tmp_path):
        generate_presentation(_TEXT)
        # tmp_path should have nothing in it
        assert list(tmp_path.iterdir()) == []

    def test_mode_deterministic_unchanged(self, tmp_path):
        result = generate_presentation(_TEXT)
        assert result.mode == "deterministic"
        assert result.artifact_paths is None


# ---------------------------------------------------------------------------
# Directory creation
# ---------------------------------------------------------------------------

class TestArtifactDirectoryCreation:
    def test_nested_dir_created(self, tmp_path):
        arts = tmp_path / "a" / "b" / "c"
        generate_presentation(_TEXT, artifacts_dir=arts)
        assert arts.exists()
        assert (arts / "spec.json").exists()
