"""Unit tests for the playbook execution engine."""

from __future__ import annotations

import pytest

from pptgen.playbook_engine import PlaybookNotFoundError, execute_playbook
from pptgen.playbook_engine.playbook_loader import load_playbook
from pptgen.spec.presentation_spec import PresentationSpec


_MEETING_TEXT = (
    "Meeting Notes\n"
    "Attendees: Alice, Bob\n"
    "Agenda:\n"
    "  1. Review progress\n"
    "  2. Plan next quarter\n"
    "Action items:\n"
    "  - Alice to draft proposal\n"
    "  - Bob to update timeline\n"
    "Decisions:\n"
    "  - Adopt new process starting Q3\n"
)

_ADO_TEXT = (
    "Sprint 12 Summary\n"
    "Sprint velocity: 38 story points completed.\n"
    "Backlog: 14 items, 3 blocked by dependency.\n"
    "Azure DevOps board updated.\n"
    "Blockers:\n"
    "  - Integration pipeline delayed\n"
)

_ARCH_TEXT = (
    "ADR-007: Message Queue Decision\n"
    "Context:\n"
    "  Current system is tightly coupled.\n"
    "Decision Record:\n"
    "  Adopt event-driven architecture.\n"
    "Options Considered:\n"
    "  Option A: Azure Service Bus\n"
    "  Option B: Kafka on AKS\n"
    "Tradeoffs:\n"
    "  Lower ops overhead vs higher throughput ceiling.\n"
)

_DEVOPS_TEXT = (
    "DORA Metrics Q2\n"
    "Deployment frequency: 3.8 deploys/day\n"
    "Lead time for changes: 1.9 hours\n"
    "MTTR: 22 minutes\n"
    "Change failure rate: 1.7%\n"
)


class TestExecutePlaybookReturnsSpec:
    def test_meeting_notes_returns_spec(self):
        spec = execute_playbook("meeting-notes-to-eos-rocks", _MEETING_TEXT)
        assert isinstance(spec, PresentationSpec)

    def test_ado_summary_returns_spec(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _ADO_TEXT)
        assert isinstance(spec, PresentationSpec)

    def test_architecture_returns_spec(self):
        spec = execute_playbook("architecture-notes-to-adr-deck", _ARCH_TEXT)
        assert isinstance(spec, PresentationSpec)

    def test_devops_metrics_returns_spec(self):
        spec = execute_playbook("devops-metrics-to-scorecard", _DEVOPS_TEXT)
        assert isinstance(spec, PresentationSpec)

    def test_generic_returns_spec(self):
        spec = execute_playbook("generic-summary-playbook", "Some random content here.")
        assert isinstance(spec, PresentationSpec)


class TestExecutePlaybookStructure:
    def test_spec_has_non_empty_title(self):
        spec = execute_playbook("meeting-notes-to-eos-rocks", _MEETING_TEXT)
        assert spec.title

    def test_spec_has_non_empty_subtitle(self):
        spec = execute_playbook("ado-summary-to-weekly-delivery", _ADO_TEXT)
        assert spec.subtitle

    def test_spec_has_at_least_one_section(self):
        spec = execute_playbook("architecture-notes-to-adr-deck", _ARCH_TEXT)
        assert len(spec.sections) >= 1

    def test_all_section_titles_non_empty(self):
        spec = execute_playbook("devops-metrics-to-scorecard", _DEVOPS_TEXT)
        for section in spec.sections:
            assert section.title


class TestExecutePlaybookDeterminism:
    def test_same_input_same_output(self):
        results = [
            execute_playbook("meeting-notes-to-eos-rocks", _MEETING_TEXT)
            for _ in range(5)
        ]
        titles = {r.title for r in results}
        assert len(titles) == 1, "execute_playbook must be deterministic"

    def test_same_input_same_section_count(self):
        results = [
            execute_playbook("ado-summary-to-weekly-delivery", _ADO_TEXT)
            for _ in range(3)
        ]
        counts = {len(r.sections) for r in results}
        assert len(counts) == 1


class TestExecutePlaybookErrors:
    def test_unknown_playbook_id_raises(self):
        with pytest.raises(PlaybookNotFoundError):
            execute_playbook("totally-nonexistent-playbook", "some text")

    def test_generic_fallback_does_not_raise(self):
        # generic-summary-playbook is not in routing table but is valid
        spec = execute_playbook("generic-summary-playbook", "any content")
        assert isinstance(spec, PresentationSpec)

    def test_empty_text_does_not_raise(self):
        for pid in [
            "meeting-notes-to-eos-rocks",
            "ado-summary-to-weekly-delivery",
            "architecture-notes-to-adr-deck",
            "devops-metrics-to-scorecard",
            "generic-summary-playbook",
        ]:
            spec = execute_playbook(pid, "")
            assert isinstance(spec, PresentationSpec)
