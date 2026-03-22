"""Unit tests for the deterministic executor."""

from __future__ import annotations

import pytest

from pptgen.playbook_engine.deterministic_executor import run
from pptgen.playbook_engine.playbook_loader import PlaybookNotFoundError
from pptgen.spec.presentation_spec import PresentationSpec


_MEETING = "Meeting notes. Attendees: Alice. Action items: review deliverables."
_ADO = "Sprint 12. Velocity 38 story points. Backlog groomed. Three blocked."
_ARCH = "ADR-007: option A vs B. Decision: event-driven. Tradeoffs documented."
_DEVOPS = "DORA: deployment frequency 4/day, change failure rate 1.8%, MTTR 12min."


class TestDeterministicExecutorReturnType:
    def test_returns_presentation_spec(self):
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        assert isinstance(spec, PresentationSpec)

    def test_all_playbooks_return_spec(self):
        cases = [
            ("meeting-notes-to-eos-rocks", _MEETING),
            ("ado-summary-to-weekly-delivery", _ADO),
            ("architecture-notes-to-adr-deck", _ARCH),
            ("devops-metrics-to-scorecard", _DEVOPS),
            ("generic-summary-playbook", "random text"),
        ]
        for pid, text in cases:
            assert isinstance(run(pid, text), PresentationSpec)


class TestDeterministicExecutorBehavior:
    def test_spec_has_non_empty_title(self):
        spec = run("ado-summary-to-weekly-delivery", _ADO)
        assert spec.title

    def test_spec_has_non_empty_subtitle(self):
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        assert spec.subtitle

    def test_spec_has_at_least_one_section(self):
        spec = run("architecture-notes-to-adr-deck", _ARCH)
        assert len(spec.sections) >= 1

    def test_is_deterministic(self):
        results = [run("meeting-notes-to-eos-rocks", _MEETING) for _ in range(5)]
        titles = {r.title for r in results}
        assert len(titles) == 1

    def test_empty_input_still_returns_spec(self):
        spec = run("generic-summary-playbook", "")
        assert isinstance(spec, PresentationSpec)


class TestDeterministicExecutorErrors:
    def test_unknown_playbook_raises(self):
        with pytest.raises(PlaybookNotFoundError):
            run("totally-unknown-playbook", "text")
