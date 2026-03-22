"""Unit tests for the route_input() public interface."""

from __future__ import annotations

import pytest

from pptgen.input_router import InputRouterError, route_input
from pptgen.input_router.classifier import FALLBACK_PLAYBOOK


# ---------------------------------------------------------------------------
# Happy-path routing
# ---------------------------------------------------------------------------

class TestRouteInputHappyPath:
    def test_meeting_notes_routed_correctly(self):
        text = (
            "Meeting Notes\n"
            "Attendees: Alice, Bob\n"
            "Agenda: review action items and decisions from last discussion."
        )
        assert route_input(text) == "meeting-notes-to-eos-rocks"

    def test_ado_sprint_summary_routed_correctly(self):
        text = (
            "Sprint 12 complete. Velocity was 38 story points. "
            "Three work items blocked. Backlog groomed. Azure DevOps updated."
        )
        assert route_input(text) == "ado-summary-to-weekly-delivery"

    def test_architecture_notes_routed_correctly(self):
        text = (
            "ADR-007: We evaluated option A vs option B. "
            "Decision record: adopt the event-driven architecture. "
            "Tradeoffs documented. System design approved."
        )
        assert route_input(text) == "architecture-notes-to-adr-deck"

    def test_devops_metrics_routed_correctly(self):
        text = (
            "DORA report: deployment frequency 3/day, "
            "change failure rate 1.8%, lead time for changes under 2h, "
            "MTTR 12 minutes. CI/CD metrics all green."
        )
        assert route_input(text) == "devops-metrics-to-scorecard"

    def test_unknown_content_returns_fallback(self):
        text = "The weather forecast shows rain on Tuesday."
        assert route_input(text) == FALLBACK_PLAYBOOK


# ---------------------------------------------------------------------------
# Return type contract
# ---------------------------------------------------------------------------

class TestRouteInputReturnType:
    def test_always_returns_string(self):
        for text in ["sprint backlog", "meeting notes", "adr option a", ""]:
            result = route_input(text)
            assert isinstance(result, str), f"Expected str, got {type(result)} for {text!r}"

    def test_returns_exactly_one_value(self):
        result = route_input("sprint backlog velocity work items")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Input normalisation
# ---------------------------------------------------------------------------

class TestRouteInputNormalisation:
    def test_leading_trailing_whitespace_stripped(self):
        result_clean = route_input("sprint backlog velocity")
        result_padded = route_input("   sprint backlog velocity   ")
        assert result_clean == result_padded

    def test_uppercase_input_normalised(self):
        result_lower = route_input("sprint backlog velocity")
        result_upper = route_input("SPRINT BACKLOG VELOCITY")
        assert result_lower == result_upper

    def test_mixed_case_normalised(self):
        result = route_input("Azure DevOps Sprint Backlog")
        assert result == "ado-summary-to-weekly-delivery"


# ---------------------------------------------------------------------------
# Edge cases — empty and whitespace
# ---------------------------------------------------------------------------

class TestRouteInputEdgeCases:
    def test_empty_string_returns_fallback(self):
        assert route_input("") == FALLBACK_PLAYBOOK

    def test_whitespace_only_returns_fallback(self):
        assert route_input("   \n\t  ") == FALLBACK_PLAYBOOK

    def test_single_word_unknown_returns_fallback(self):
        assert route_input("banana") == FALLBACK_PLAYBOOK

    def test_newlines_in_input_handled(self):
        text = "meeting\nattendees\naction items\nfollow-up"
        assert route_input(text) == "meeting-notes-to-eos-rocks"


# ---------------------------------------------------------------------------
# Invalid input types
# ---------------------------------------------------------------------------

class TestRouteInputInvalidTypes:
    def test_none_raises_input_router_error(self):
        with pytest.raises(InputRouterError, match="str"):
            route_input(None)  # type: ignore[arg-type]

    def test_int_raises_input_router_error(self):
        with pytest.raises(InputRouterError):
            route_input(42)  # type: ignore[arg-type]

    def test_list_raises_input_router_error(self):
        with pytest.raises(InputRouterError):
            route_input(["sprint", "backlog"])  # type: ignore[arg-type]

    def test_error_message_includes_type_name(self):
        with pytest.raises(InputRouterError, match="NoneType"):
            route_input(None)  # type: ignore[arg-type]
