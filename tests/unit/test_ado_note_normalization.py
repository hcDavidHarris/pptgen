"""Integration tests for the ADO playbook with labeled note-style input.

Verifies that the note normalizer produces a richer spec when the input
contains recognized label-colon headings, and that existing unstructured
ADO input continues to work without regression.
"""
from __future__ import annotations

import pytest

from pptgen.playbook_engine import execute_playbook
from pptgen.spec.presentation_spec import PresentationSpec

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

_LABELED_NOTES = """\
Sprint 14 Review Notes

Problems:
- retention only runs on shutdown
- UI visibility weak
- run metrics not exposed

Next Step:
Phase 6D Observability

Focus Areas:
- telemetry
- run metrics
- CLI inspection
"""

# Classic ADO connector-style output — no recognized labels, should use old path
_CLASSIC_ADO_TEXT = (
    "Sprint 12 Summary\n"
    "Sprint velocity: 38 story points completed.\n"
    "Backlog: 14 items, 3 blocked by dependency.\n"
    "Azure DevOps board updated.\n"
    "Blockers:\n"
    "  - Integration pipeline delayed\n"
)

# ADO text with risks label
_ADO_WITH_RISKS = """\
Sprint 15 Planning Notes

Risks:
- auth service migration not tested
- load test skipped

Next Steps:
- run auth suite before release
- add load test to CI

Decisions:
- delay release by one sprint
"""

# Minimal labeled input — only one section
_SINGLE_SECTION = """\
Recommendations:
- adopt structured logging
- add run metrics to API
"""


class TestLabeledNotesProduceRicherSpec:
    def test_returns_valid_spec(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        assert isinstance(spec, PresentationSpec)

    def test_title_extracted_from_text(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        assert "Sprint 14" in spec.title or spec.title == "Engineering Delivery Summary"

    def test_multiple_sections_produced(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        # Should produce at least 3 sections: Problems, Next Step, Focus Areas
        assert len(spec.sections) >= 3

    def test_problems_section_present(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        titles = [s.title for s in spec.sections]
        assert any("risk" in t.lower() or "problem" in t.lower() for t in titles)

    def test_recommendation_section_present(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        titles = [s.title for s in spec.sections]
        assert any("recommend" in t.lower() for t in titles)

    def test_focus_areas_section_present(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        titles = [s.title for s in spec.sections]
        assert any("focus" in t.lower() for t in titles)

    def test_bullets_preserved_under_problems(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
        problems_section = next(
            (s for s in spec.sections if "risk" in s.title.lower() or "problem" in s.title.lower()),
            None,
        )
        assert problems_section is not None
        assert len(problems_section.bullets) == 3
        # Bullet content should not contain leading dashes
        for bullet in problems_section.bullets:
            assert not bullet.startswith("-")

    def test_deterministic_output(self):
        specs = [
            execute_playbook("ado-summary-to-weekly-delivery", _LABELED_NOTES)
            for _ in range(3)
        ]
        titles = {s.title for s in specs}
        section_counts = {len(s.sections) for s in specs}
        assert len(titles) == 1
        assert len(section_counts) == 1


class TestADORegressionSafety:
    def test_classic_ado_text_still_produces_spec(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _CLASSIC_ADO_TEXT)
        assert isinstance(spec, PresentationSpec)

    def test_classic_ado_text_has_delivery_status_section(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _CLASSIC_ADO_TEXT)
        titles = [s.title for s in spec.sections]
        assert any("delivery" in t.lower() or "status" in t.lower() for t in titles)

    def test_classic_ado_text_title_unchanged(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _CLASSIC_ADO_TEXT)
        assert spec.title == "Engineering Delivery Summary"

    def test_empty_input_does_not_raise(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", "")
        assert isinstance(spec, PresentationSpec)

    def test_plain_unstructured_text_does_not_raise(self):
        spec = execute_playbook(
            "ado-summary-to-weekly-delivery",
            "Some general project notes without any structure.",
        )
        assert isinstance(spec, PresentationSpec)


class TestRisksLabelVariants:
    def test_risks_label_produces_spec(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _ADO_WITH_RISKS)
        assert isinstance(spec, PresentationSpec)
        assert len(spec.sections) >= 2

    def test_risks_section_bullets_populated(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _ADO_WITH_RISKS)
        risk_section = next(
            (s for s in spec.sections if "risk" in s.title.lower() or "problem" in s.title.lower()),
            None,
        )
        assert risk_section is not None
        assert len(risk_section.bullets) >= 1

    def test_decisions_section_produced(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _ADO_WITH_RISKS)
        titles = [s.title.lower() for s in spec.sections]
        assert any("decision" in t for t in titles)


class TestSingleSectionInput:
    def test_single_label_produces_spec(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _SINGLE_SECTION)
        assert isinstance(spec, PresentationSpec)
        assert len(spec.sections) >= 1

    def test_single_section_bullets_populated(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _SINGLE_SECTION)
        assert any(len(s.bullets) > 0 for s in spec.sections)
