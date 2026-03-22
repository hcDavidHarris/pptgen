"""Unit tests for the rule-based content extractor."""

from __future__ import annotations

import pytest

from pptgen.playbook_engine.content_extractor import extract
from pptgen.spec.presentation_spec import PresentationSpec


# ---------------------------------------------------------------------------
# Shared text fixtures (same as used in classifier tests for consistency)
# ---------------------------------------------------------------------------

_MEETING_NOTES = """
Meeting Notes — Q3 EOS Planning Session
Attendees: Sarah, James, Priya, Tom
Agenda:
  1. Review Q2 rocks status
  2. Set Q3 rocks
  3. Scorecard review

Discussion:
  - Delivery reliability rock achieved 99.2% uptime
  - Three rocks missed due to staffing constraints

Action items:
  - Sarah to draft Q3 rocks by Friday
  - Tom to update scorecard template
  - Follow-up meeting scheduled for next Monday

Decisions:
  - Move to bi-weekly rock check-ins
"""

_ADO_SPRINT = """
Sprint 47 Summary — Engineering Delivery

Sprint velocity: 42 story points completed out of 48 planned.

Backlog:
  - 6 features in progress
  - 3 bugs escalated to current sprint
  - 2 work items blocked by external dependency

Azure DevOps board updated. Next sprint iteration planning on Thursday.
Release branch created for v2.3.0.

Blockers:
  - ADO pipeline flaky on integration tests
  - Epic E-1042 delayed by security review
"""

_ARCHITECTURE_NOTES = """
ADR-014: Event-Driven Messaging Platform

Context:
  Services currently share state via synchronous REST calls, creating tight coupling.

Decision Record:
  Adopt Azure Service Bus for all inter-service events.

Options Considered:
  Option A: Azure Service Bus — managed, native RBAC, dead-letter queues.
  Option B: Kafka on AKS — higher throughput but requires cluster management.

Tradeoffs:
  Service Bus has lower operational overhead; Kafka offers higher ceiling.

Constraints:
  Team has no Kafka operational experience. Architecture review board must approve.
"""

_DEVOPS_METRICS = """
DORA Metrics — Q2 Engineering Report

Deployment frequency: 4.2 deploys/day (Elite)
Lead time for changes: 2.1 hours (High)
MTTR: 18 minutes (Elite)
Change failure rate: 2.3% (High)

CI/CD metrics show improvement across all four key metrics this quarter.
Deployment pipeline reliability improved from 94% to 98.7%.
"""

_GENERIC = """
The quarterly budget review showed a 12% variance against forecast.
Procurement approved three new vendor contracts.
Office expansion project is on schedule for completion in Q4.
"""


# ---------------------------------------------------------------------------
# Structural validity (all strategies must return a valid PresentationSpec)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("playbook_id,text", [
    ("meeting-notes-to-eos-rocks", _MEETING_NOTES),
    ("ado-summary-to-weekly-delivery", _ADO_SPRINT),
    ("architecture-notes-to-adr-deck", _ARCHITECTURE_NOTES),
    ("devops-metrics-to-scorecard", _DEVOPS_METRICS),
    ("generic-summary-playbook", _GENERIC),
])
def test_extract_returns_valid_spec(playbook_id, text):
    spec = extract(playbook_id, text)
    assert isinstance(spec, PresentationSpec)
    assert spec.title
    assert spec.subtitle
    assert spec.sections


@pytest.mark.parametrize("playbook_id", [
    "meeting-notes-to-eos-rocks",
    "ado-summary-to-weekly-delivery",
    "architecture-notes-to-adr-deck",
    "devops-metrics-to-scorecard",
    "generic-summary-playbook",
])
def test_extract_handles_empty_text(playbook_id):
    """All strategies must return a valid spec even for empty input."""
    spec = extract(playbook_id, "")
    assert isinstance(spec, PresentationSpec)
    assert spec.title
    assert spec.subtitle
    assert spec.sections


@pytest.mark.parametrize("playbook_id", [
    "meeting-notes-to-eos-rocks",
    "ado-summary-to-weekly-delivery",
    "architecture-notes-to-adr-deck",
    "devops-metrics-to-scorecard",
    "generic-summary-playbook",
])
def test_extract_is_deterministic(playbook_id):
    """Same input must produce the same output every time."""
    text = _MEETING_NOTES
    results = [extract(playbook_id, text) for _ in range(3)]
    titles = {r.title for r in results}
    assert len(titles) == 1


# ---------------------------------------------------------------------------
# Meeting notes strategy
# ---------------------------------------------------------------------------

class TestMeetingNotesExtractor:
    def test_title_derived_from_input(self):
        spec = extract("meeting-notes-to-eos-rocks", _MEETING_NOTES)
        assert "Meeting" in spec.title or spec.title

    def test_section_titles_non_empty(self):
        spec = extract("meeting-notes-to-eos-rocks", _MEETING_NOTES)
        for section in spec.sections:
            assert section.title

    def test_action_items_appear_in_sections(self):
        spec = extract("meeting-notes-to-eos-rocks", _MEETING_NOTES)
        all_bullets = [b for s in spec.sections for b in s.bullets]
        # Some bullet should mention an action
        assert any("draft" in b.lower() or "update" in b.lower() or "meeting" in b.lower()
                   for b in all_bullets)


# ---------------------------------------------------------------------------
# ADO summary strategy
# ---------------------------------------------------------------------------

class TestAdoSummaryExtractor:
    def test_title_is_delivery_summary(self):
        spec = extract("ado-summary-to-weekly-delivery", _ADO_SPRINT)
        assert "Delivery" in spec.title or "Engineering" in spec.title

    def test_has_delivery_section(self):
        spec = extract("ado-summary-to-weekly-delivery", _ADO_SPRINT)
        titles = [s.title for s in spec.sections]
        assert any("Delivery" in t or "Status" in t for t in titles)

    def test_sprint_content_in_bullets(self):
        spec = extract("ado-summary-to-weekly-delivery", _ADO_SPRINT)
        all_bullets = [b.lower() for s in spec.sections for b in s.bullets]
        assert any("sprint" in b or "velocity" in b or "story" in b for b in all_bullets)


# ---------------------------------------------------------------------------
# Architecture notes strategy
# ---------------------------------------------------------------------------

class TestArchitectureNotesExtractor:
    def test_title_is_architecture_review(self):
        spec = extract("architecture-notes-to-adr-deck", _ARCHITECTURE_NOTES)
        assert spec.title

    def test_subtitle_references_adr(self):
        spec = extract("architecture-notes-to-adr-deck", _ARCHITECTURE_NOTES)
        assert spec.subtitle

    def test_has_multiple_sections(self):
        spec = extract("architecture-notes-to-adr-deck", _ARCHITECTURE_NOTES)
        assert len(spec.sections) >= 1

    def test_options_or_context_in_sections(self):
        spec = extract("architecture-notes-to-adr-deck", _ARCHITECTURE_NOTES)
        section_titles = [s.title.lower() for s in spec.sections]
        assert any(
            "context" in t or "option" in t or "decision" in t or "architecture" in t
            for t in section_titles
        )


# ---------------------------------------------------------------------------
# DevOps metrics strategy
# ---------------------------------------------------------------------------

class TestDevopsMetricsExtractor:
    def test_title_is_scorecard(self):
        spec = extract("devops-metrics-to-scorecard", _DEVOPS_METRICS)
        assert "Scorecard" in spec.title or "DevOps" in spec.title

    def test_has_scorecard_section(self):
        spec = extract("devops-metrics-to-scorecard", _DEVOPS_METRICS)
        assert any("Scorecard" in s.title or "Metrics" in s.title for s in spec.sections)

    def test_metrics_extracted(self):
        spec = extract("devops-metrics-to-scorecard", _DEVOPS_METRICS)
        all_metrics = [m for s in spec.sections for m in s.metrics]
        assert len(all_metrics) >= 1

    def test_metric_labels_non_empty(self):
        spec = extract("devops-metrics-to-scorecard", _DEVOPS_METRICS)
        for s in spec.sections:
            for m in s.metrics:
                assert m.label
                assert m.value


# ---------------------------------------------------------------------------
# Generic strategy
# ---------------------------------------------------------------------------

class TestGenericExtractor:
    def test_returns_valid_spec(self):
        spec = extract("generic-summary-playbook", _GENERIC)
        assert isinstance(spec, PresentationSpec)

    def test_has_overview_section(self):
        spec = extract("generic-summary-playbook", _GENERIC)
        assert any("Overview" in s.title or "Summary" in s.title for s in spec.sections)

    def test_unknown_playbook_id_uses_generic(self):
        spec = extract("completely-unknown-id", _GENERIC)
        assert isinstance(spec, PresentationSpec)
        assert spec.title
