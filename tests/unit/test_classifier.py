"""Unit tests for the heuristic input classifier."""

from __future__ import annotations

import pytest

from pptgen.input_router.classifier import FALLBACK_PLAYBOOK, _PRIORITY, classify


# ---------------------------------------------------------------------------
# Text fixtures — deterministic, self-contained
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

_ADO_SPRINT_SUMMARY = """
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

System context: all 7 microservices will publish events via topics.
Component dependencies to be documented in the architecture overview.
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

_UNKNOWN = """
The quarterly budget review showed a 12% variance against forecast.
Procurement approved three new vendor contracts.
Office expansion project is on schedule for completion in Q4.
"""


# ---------------------------------------------------------------------------
# Per-category routing
# ---------------------------------------------------------------------------

class TestClassifyMeetingNotes:
    def test_routes_to_meeting_notes(self):
        assert classify(_MEETING_NOTES.lower()) == "meeting-notes-to-eos-rocks"

    def test_minimal_meeting_signal(self):
        assert classify("meeting with attendees to discuss action items") == "meeting-notes-to-eos-rocks"


class TestClassifyAdoSummary:
    def test_routes_to_ado_summary(self):
        assert classify(_ADO_SPRINT_SUMMARY.lower()) == "ado-summary-to-weekly-delivery"

    def test_minimal_ado_signal(self):
        assert classify("sprint backlog velocity story points") == "ado-summary-to-weekly-delivery"

    def test_blocked_work_items(self):
        result = classify("blocked work items in the sprint backlog")
        assert result == "ado-summary-to-weekly-delivery"


class TestClassifyArchitectureNotes:
    def test_routes_to_architecture_adr(self):
        assert classify(_ARCHITECTURE_NOTES.lower()) == "architecture-notes-to-adr-deck"

    def test_minimal_adr_signal(self):
        assert classify("adr decision record tradeoff option a option b") == "architecture-notes-to-adr-deck"

    def test_architecture_with_constraints(self):
        result = classify("architecture review: constraints, interface, dependencies, design decision")
        assert result == "architecture-notes-to-adr-deck"


class TestClassifyDevopsMetrics:
    def test_routes_to_devops_scorecard(self):
        assert classify(_DEVOPS_METRICS.lower()) == "devops-metrics-to-scorecard"

    def test_dora_signal(self):
        assert classify("dora metrics deployment frequency change failure rate") == "devops-metrics-to-scorecard"

    def test_mttr_signal(self):
        assert classify("mttr mean time to restore four key metrics") == "devops-metrics-to-scorecard"


class TestClassifyUnknown:
    def test_unknown_returns_fallback(self):
        assert classify(_UNKNOWN.lower()) == FALLBACK_PLAYBOOK

    def test_empty_string_returns_fallback(self):
        assert classify("") == FALLBACK_PLAYBOOK

    def test_whitespace_only_returns_fallback(self):
        assert classify("   ") == FALLBACK_PLAYBOOK

    def test_random_words_return_fallback(self):
        assert classify("banana orange purple seventeen") == FALLBACK_PLAYBOOK


# ---------------------------------------------------------------------------
# Determinism and tie-breaking
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_repeated_calls_return_same_result(self):
        text = _ADO_SPRINT_SUMMARY.lower()
        results = {classify(text) for _ in range(10)}
        assert len(results) == 1

    def test_architecture_beats_meeting_on_tie(self):
        """architecture-notes-to-adr-deck has higher priority than meeting-notes."""
        # Craft text that scores equally for both
        tie_text = "meeting architecture"
        result = classify(tie_text)
        assert result == "architecture-notes-to-adr-deck"

    def test_ado_beats_meeting_on_tie(self):
        """ado-summary-to-weekly-delivery has higher priority than meeting-notes."""
        tie_text = "sprint meeting"
        result = classify(tie_text)
        assert result == "ado-summary-to-weekly-delivery"

    def test_priority_order_is_complete(self):
        """Every classifiable route must appear in the priority tuple."""
        from pptgen.input_router.classifier import _SIGNALS
        for route in _SIGNALS:
            assert route in _PRIORITY, f"{route!r} not in _PRIORITY"

    def test_fallback_is_last_in_priority(self):
        assert _PRIORITY[-1] == FALLBACK_PLAYBOOK
