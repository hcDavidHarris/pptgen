"""Tests confirming that labeled note input is normalized regardless of which
deterministic playbook the classifier selects.

The note normalizer is now triggered at the ``extract()`` dispatcher level, so
any playbook receiving labeled-section text should produce a multi-section spec
rather than collapsing everything into a single sparse section.
"""
from __future__ import annotations

import pytest

from pptgen.playbook_engine.content_extractor import extract
from pptgen.spec.presentation_spec import PresentationSpec


# ---------------------------------------------------------------------------
# Shared labeled input — realistic "Platform Delivery Review" format
# ---------------------------------------------------------------------------

_PLATFORM_DELIVERY_NOTES = """\
Platform Delivery Review — pptgen

Problems:
- retention only runs on shutdown
- UI visibility weak
- run metrics not exposed

Decisions:
- delay release by one sprint
- adopt structured logging

Open Questions:
- what is the SLA for artifact promotion?
- should CLI read SQLite directly?

Next Steps:
- run auth suite before release
- add load test to CI
"""

_SINGLE_SECTION_LABELED = """\
Focus Areas:
- telemetry
- run metrics
- CLI inspection
"""


# ---------------------------------------------------------------------------
# Labeled input fires for meeting-notes playbook
# ---------------------------------------------------------------------------

class TestMeetingNotesPlaybookWithLabeledInput:
    def test_returns_valid_spec(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLATFORM_DELIVERY_NOTES)
        assert isinstance(spec, PresentationSpec)

    def test_multiple_sections_produced(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLATFORM_DELIVERY_NOTES)
        assert len(spec.sections) >= 3

    def test_decisions_section_present(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLATFORM_DELIVERY_NOTES)
        titles = [s.title.lower() for s in spec.sections]
        assert any("decision" in t for t in titles)

    def test_problems_section_present(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLATFORM_DELIVERY_NOTES)
        titles = [s.title.lower() for s in spec.sections]
        assert any("risk" in t or "problem" in t for t in titles)

    def test_open_questions_section_present(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLATFORM_DELIVERY_NOTES)
        titles = [s.title.lower() for s in spec.sections]
        assert any("question" in t for t in titles)

    def test_bullets_not_empty(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLATFORM_DELIVERY_NOTES)
        for section in spec.sections:
            assert all(not b.startswith("-") for b in section.bullets)


# ---------------------------------------------------------------------------
# Labeled input fires for architecture playbook
# ---------------------------------------------------------------------------

class TestArchitecturePlaybookWithLabeledInput:
    def test_returns_valid_spec(self):
        spec = extract("architecture-notes-to-adr-deck", _PLATFORM_DELIVERY_NOTES)
        assert isinstance(spec, PresentationSpec)

    def test_multiple_sections_produced(self):
        spec = extract("architecture-notes-to-adr-deck", _PLATFORM_DELIVERY_NOTES)
        assert len(spec.sections) >= 3

    def test_decisions_section_present(self):
        spec = extract("architecture-notes-to-adr-deck", _PLATFORM_DELIVERY_NOTES)
        titles = [s.title.lower() for s in spec.sections]
        assert any("decision" in t for t in titles)


# ---------------------------------------------------------------------------
# Labeled input fires for devops-metrics playbook
# ---------------------------------------------------------------------------

class TestDevopsPlaybookWithLabeledInput:
    def test_returns_valid_spec(self):
        spec = extract("devops-metrics-to-scorecard", _PLATFORM_DELIVERY_NOTES)
        assert isinstance(spec, PresentationSpec)

    def test_multiple_sections_produced(self):
        spec = extract("devops-metrics-to-scorecard", _PLATFORM_DELIVERY_NOTES)
        assert len(spec.sections) >= 3


# ---------------------------------------------------------------------------
# Labeled input fires for generic playbook
# ---------------------------------------------------------------------------

class TestGenericPlaybookWithLabeledInput:
    def test_returns_valid_spec(self):
        spec = extract("generic-summary-playbook", _PLATFORM_DELIVERY_NOTES)
        assert isinstance(spec, PresentationSpec)

    def test_multiple_sections_produced(self):
        spec = extract("generic-summary-playbook", _PLATFORM_DELIVERY_NOTES)
        assert len(spec.sections) >= 3

    def test_single_labeled_section_falls_through_to_generic(self):
        # Only one recognized label — below the two-label threshold, so the
        # generic extractor runs and still produces a valid spec with bullets.
        spec = extract("generic-summary-playbook", _SINGLE_SECTION_LABELED)
        assert isinstance(spec, PresentationSpec)
        assert len(spec.sections) >= 1
        assert any(len(s.bullets) > 0 for s in spec.sections)


# ---------------------------------------------------------------------------
# Regression: non-labeled prose still uses playbook-specific path
# ---------------------------------------------------------------------------

_PLAIN_MEETING_TEXT = (
    "Q1 planning meeting\n"
    "Agenda:\n"
    "- roadmap review\n"
    "- budget sign-off\n"
    "Action Items:\n"
    "- Alice to draft charter\n"
    "- Bob to schedule follow-up\n"
)

_PLAIN_ADO_TEXT = (
    "Sprint 12 Summary\n"
    "Sprint velocity: 38 story points completed.\n"
    "Backlog: 14 items, 3 blocked by dependency.\n"
    "Azure DevOps board updated.\n"
)


class TestNonLabeledProseUnchanged:
    def test_meeting_notes_prose_still_produces_spec(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLAIN_MEETING_TEXT)
        assert isinstance(spec, PresentationSpec)

    def test_meeting_notes_prose_has_action_items_section(self):
        spec = extract("meeting-notes-to-eos-rocks", _PLAIN_MEETING_TEXT)
        titles = [s.title.lower() for s in spec.sections]
        assert any("action" in t for t in titles)

    def test_ado_prose_produces_delivery_status_section(self):
        spec = extract("ado-summary-to-weekly-delivery", _PLAIN_ADO_TEXT)
        titles = [s.title.lower() for s in spec.sections]
        assert any("delivery" in t or "status" in t for t in titles)

    def test_ado_prose_title_is_fixed_string(self):
        spec = extract("ado-summary-to-weekly-delivery", _PLAIN_ADO_TEXT)
        assert spec.title == "Engineering Delivery Summary"

    def test_empty_input_does_not_raise_for_any_playbook(self):
        for pid in [
            "meeting-notes-to-eos-rocks",
            "ado-summary-to-weekly-delivery",
            "architecture-notes-to-adr-deck",
            "devops-metrics-to-scorecard",
            "generic-summary-playbook",
        ]:
            spec = extract(pid, "")
            assert isinstance(spec, PresentationSpec)

    def test_unknown_playbook_id_uses_generic_path(self):
        spec = extract("nonexistent-playbook-xyz", _PLAIN_ADO_TEXT)
        assert isinstance(spec, PresentationSpec)
