"""Unit tests for the artifact writer."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from pptgen.artifacts import write_artifacts
from pptgen.pipeline import generate_presentation
from pptgen.planner.slide_plan import PlannedSlide, SlidePlan
from pptgen.spec.presentation_spec import PresentationSpec, SectionSpec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SPEC = PresentationSpec(
    title="Test Title",
    subtitle="Test Subtitle",
    sections=[SectionSpec(title="Section A", bullets=["bullet 1", "bullet 2"])],
)

_PLAN = SlidePlan(
    playbook_id="generic-summary-playbook",
    slide_count=2,
    planned_slide_types=["title", "bullets"],
    section_count=1,
    slides=[
        PlannedSlide(slide_type="title", title="Test Title"),
        PlannedSlide(slide_type="bullets", title="Section A", source_section_title="Section A"),
    ],
)

_DECK = {
    "template": "ops_review_v1",
    "slides": [
        {"type": "title", "title": "Test Title"},
        {"type": "bullets", "title": "Section A", "bullets": ["bullet 1", "bullet 2"]},
    ],
}


# ---------------------------------------------------------------------------
# Basic writes
# ---------------------------------------------------------------------------

class TestWriteArtifactsFiles:
    def test_creates_three_files(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        assert (tmp_path / "spec.json").exists()
        assert (tmp_path / "slide_plan.json").exists()
        assert (tmp_path / "deck_definition.json").exists()

    def test_returns_path_mapping(self, tmp_path):
        paths = write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        assert set(paths.keys()) == {"spec", "slide_plan", "deck_definition"}

    def test_returned_paths_are_path_objects(self, tmp_path):
        paths = write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        for p in paths.values():
            assert isinstance(p, Path)

    def test_returned_paths_exist(self, tmp_path):
        paths = write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        for p in paths.values():
            assert p.exists()

    def test_creates_directory_if_missing(self, tmp_path):
        new_dir = tmp_path / "nested" / "artifacts"
        assert not new_dir.exists()
        write_artifacts(new_dir, _SPEC, _PLAN, _DECK)
        assert new_dir.exists()


# ---------------------------------------------------------------------------
# JSON validity
# ---------------------------------------------------------------------------

class TestArtifactJSON:
    def test_spec_json_is_valid(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "spec.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_slide_plan_json_is_valid(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "slide_plan.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_deck_definition_json_is_valid(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "deck_definition.json").read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_spec_json_contains_title(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "spec.json").read_text(encoding="utf-8"))
        assert data["title"] == "Test Title"

    def test_spec_json_contains_sections(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "spec.json").read_text(encoding="utf-8"))
        assert isinstance(data["sections"], list)
        assert len(data["sections"]) == 1

    def test_slide_plan_json_contains_slide_count(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "slide_plan.json").read_text(encoding="utf-8"))
        assert data["slide_count"] == 2

    def test_slide_plan_json_contains_slides(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "slide_plan.json").read_text(encoding="utf-8"))
        assert isinstance(data["slides"], list)
        assert len(data["slides"]) == 2

    def test_deck_definition_json_contains_slides(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        data = json.loads((tmp_path / "deck_definition.json").read_text(encoding="utf-8"))
        assert "slides" in data

    def test_json_is_utf8(self, tmp_path):
        spec = PresentationSpec(
            title="Titre avec accents: café",
            subtitle="Résumé",
            sections=[SectionSpec(title="Sec", bullets=["point"])],
        )
        write_artifacts(tmp_path, spec, _PLAN, _DECK)
        raw = (tmp_path / "spec.json").read_bytes()
        decoded = raw.decode("utf-8")
        assert "café" in decoded

    def test_json_is_indented(self, tmp_path):
        write_artifacts(tmp_path, _SPEC, _PLAN, _DECK)
        raw = (tmp_path / "spec.json").read_text(encoding="utf-8")
        # Indented JSON contains newlines and leading spaces
        assert "\n" in raw
        assert "  " in raw


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestArtifactDeterminism:
    def test_repeated_writes_produce_identical_spec(self, tmp_path):
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        write_artifacts(dir1, _SPEC, _PLAN, _DECK)
        write_artifacts(dir2, _SPEC, _PLAN, _DECK)
        assert (dir1 / "spec.json").read_text() == (dir2 / "spec.json").read_text()

    def test_repeated_writes_produce_identical_plan(self, tmp_path):
        dir1 = tmp_path / "run1"
        dir2 = tmp_path / "run2"
        write_artifacts(dir1, _SPEC, _PLAN, _DECK)
        write_artifacts(dir2, _SPEC, _PLAN, _DECK)
        assert (dir1 / "slide_plan.json").read_text() == (dir2 / "slide_plan.json").read_text()


# ---------------------------------------------------------------------------
# Serialization of real pipeline objects
# ---------------------------------------------------------------------------

class TestArtifactSerializesRealObjects:
    def test_real_pipeline_spec_serializes(self, tmp_path):
        result = generate_presentation("sprint backlog velocity notes")
        write_artifacts(tmp_path, result.presentation_spec, result.slide_plan, result.deck_definition)
        assert (tmp_path / "spec.json").exists()

    def test_real_pipeline_slide_plan_serializes(self, tmp_path):
        result = generate_presentation("meeting notes action items")
        write_artifacts(tmp_path, result.presentation_spec, result.slide_plan, result.deck_definition)
        data = json.loads((tmp_path / "slide_plan.json").read_text(encoding="utf-8"))
        assert "slide_count" in data
        assert data["slide_count"] >= 1
