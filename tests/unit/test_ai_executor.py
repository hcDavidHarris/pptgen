"""Unit tests for the AI executor."""

from __future__ import annotations

import pytest

from pptgen.ai.models import MockModel
from pptgen.playbook_engine.ai_executor import (
    _build_prompt,
    _parse_spec,
    _synthesize_bullets,
    run,
)
from pptgen.spec.presentation_spec import PresentationSpec


_MEETING = "Meeting notes. Attendees: Alice, Bob. Action items: review deliverables."
_ADO = "Sprint 12 Summary. Velocity 38 story points. Three blocked items."
_ARCH = "ADR-007: option A vs B. Decision: event-driven architecture."
_DEVOPS = "DORA metrics: deployment frequency 4/day. Change failure rate 1.8%."


# ---------------------------------------------------------------------------
# run() entry point
# ---------------------------------------------------------------------------

class TestAIExecutorRun:
    def test_returns_presentation_spec(self):
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        assert isinstance(spec, PresentationSpec)

    def test_spec_has_non_empty_title(self):
        spec = run("ado-summary-to-weekly-delivery", _ADO)
        assert spec.title

    def test_spec_has_non_empty_subtitle(self):
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        assert spec.subtitle

    def test_spec_has_at_least_one_section(self):
        spec = run("architecture-notes-to-adr-deck", _ARCH)
        assert len(spec.sections) >= 1

    def test_all_playbooks_return_spec(self):
        cases = [
            ("meeting-notes-to-eos-rocks", _MEETING),
            ("ado-summary-to-weekly-delivery", _ADO),
            ("architecture-notes-to-adr-deck", _ARCH),
            ("devops-metrics-to-scorecard", _DEVOPS),
            ("generic-summary-playbook", "random content"),
        ]
        for pid, text in cases:
            assert isinstance(run(pid, text), PresentationSpec)

    def test_empty_input_returns_valid_spec(self):
        spec = run("generic-summary-playbook", "")
        assert isinstance(spec, PresentationSpec)
        assert spec.title
        assert spec.sections


class TestAIExecutorDeterminism:
    def test_same_input_same_title(self):
        results = [run("meeting-notes-to-eos-rocks", _MEETING) for _ in range(5)]
        titles = {r.title for r in results}
        assert len(titles) == 1

    def test_same_input_same_section_count(self):
        results = [run("ado-summary-to-weekly-delivery", _ADO) for _ in range(3)]
        counts = {len(r.sections) for r in results}
        assert len(counts) == 1


class TestAIExecutorDifferentFromDeterministic:
    """AI executor should produce structurally different output for the same input."""

    def test_ai_subtitle_differs_from_deterministic(self):
        """AI executor marks subtitle with '(AI)' label."""
        spec = run("ado-summary-to-weekly-delivery", _ADO)
        assert "(AI)" in spec.subtitle

    def test_ai_section_titles_are_synthesized(self):
        """AI executor uses synthesized section names like 'Key Points'."""
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        section_titles = [s.title for s in spec.sections]
        # AI executor uses "Key Points" or "Context & Notes"
        assert any(t in ("Key Points", "Context & Notes", "Overview") for t in section_titles)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_returns_string(self):
        assert isinstance(_build_prompt("test-playbook", "some text"), str)

    def test_includes_playbook_id(self):
        prompt = _build_prompt("meeting-notes-to-eos-rocks", "text")
        assert "meeting-notes-to-eos-rocks" in prompt

    def test_includes_input_text(self):
        prompt = _build_prompt("test", "unique_input_marker")
        assert "unique_input_marker" in prompt

    def test_empty_input_handled(self):
        prompt = _build_prompt("test", "")
        assert "(empty)" in prompt


class TestSynthesizeBullets:
    def test_returns_list(self):
        assert isinstance(_synthesize_bullets(["a", "b"]), list)

    def test_deduplicates(self):
        bullets = _synthesize_bullets(["same", "same", "other"])
        assert bullets.count("same") == 1

    def test_respects_max_bullets(self):
        lines = [f"item {i}" for i in range(20)]
        bullets = _synthesize_bullets(lines, max_bullets=3)
        assert len(bullets) <= 3

    def test_empty_input_returns_fallback(self):
        bullets = _synthesize_bullets([])
        assert len(bullets) == 1


class TestParseSpec:
    def test_valid_dict_returns_spec(self):
        raw = {
            "title": "My Title",
            "subtitle": "My Subtitle",
            "sections": [{"title": "Sec", "bullets": ["b1"]}],
        }
        spec = _parse_spec(raw)
        assert isinstance(spec, PresentationSpec)

    def test_missing_title_gets_fallback(self):
        raw = {"subtitle": "Sub", "sections": [{"title": "S", "bullets": []}]}
        spec = _parse_spec(raw)
        assert spec.title == "AI Presentation"

    def test_missing_subtitle_gets_fallback(self):
        raw = {"title": "T", "sections": [{"title": "S", "bullets": []}]}
        spec = _parse_spec(raw)
        assert spec.subtitle == "AI-assisted generation"

    def test_empty_sections_gets_overview_fallback(self):
        raw = {"title": "T", "subtitle": "S", "sections": []}
        spec = _parse_spec(raw)
        assert len(spec.sections) >= 1
        assert spec.sections[0].title == "Overview"
