"""Unit tests for the execution strategy dispatcher."""

from __future__ import annotations

import pytest

from pptgen.playbook_engine.execution_strategy import (
    AI,
    DETERMINISTIC,
    VALID_STRATEGIES,
    ExecutionMode,
    UnknownStrategyError,
    dispatch,
)
from pptgen.spec.presentation_spec import PresentationSpec


class TestExecutionModeEnum:
    def test_deterministic_member_exists(self):
        assert ExecutionMode.DETERMINISTIC

    def test_ai_member_exists(self):
        assert ExecutionMode.AI

    def test_deterministic_value_is_string(self):
        assert ExecutionMode.DETERMINISTIC.value == "deterministic"

    def test_ai_value_is_string(self):
        assert ExecutionMode.AI.value == "ai"

    def test_enum_is_str_subclass(self):
        assert isinstance(ExecutionMode.DETERMINISTIC, str)

    def test_enum_equals_plain_string(self):
        assert ExecutionMode.DETERMINISTIC == "deterministic"
        assert ExecutionMode.AI == "ai"

    def test_from_string_deterministic(self):
        assert ExecutionMode("deterministic") is ExecutionMode.DETERMINISTIC

    def test_from_string_ai(self):
        assert ExecutionMode("ai") is ExecutionMode.AI

    def test_invalid_string_raises_value_error(self):
        with pytest.raises(ValueError):
            ExecutionMode("bad-mode")


class TestStrategyConstants:
    def test_deterministic_constant(self):
        assert DETERMINISTIC == "deterministic"

    def test_ai_constant(self):
        assert AI == "ai"

    def test_valid_strategies_contains_both(self):
        assert DETERMINISTIC in VALID_STRATEGIES
        assert AI in VALID_STRATEGIES

    def test_valid_strategies_is_frozenset(self):
        assert isinstance(VALID_STRATEGIES, frozenset)

    def test_valid_strategies_derived_from_enum(self):
        assert VALID_STRATEGIES == frozenset(m.value for m in ExecutionMode)


class TestDispatchAcceptsEnum:
    def test_dispatch_with_enum_deterministic(self):
        spec = dispatch("meeting-notes-to-eos-rocks", "meeting notes", ExecutionMode.DETERMINISTIC)
        assert isinstance(spec, PresentationSpec)

    def test_dispatch_with_enum_ai(self):
        spec = dispatch("meeting-notes-to-eos-rocks", "meeting notes", ExecutionMode.AI)
        assert isinstance(spec, PresentationSpec)

    def test_dispatch_string_and_enum_same_result(self):
        text = "sprint backlog velocity"
        spec_str = dispatch("ado-summary-to-weekly-delivery", text, "deterministic")
        spec_enum = dispatch("ado-summary-to-weekly-delivery", text, ExecutionMode.DETERMINISTIC)
        assert spec_str.title == spec_enum.title


class TestDispatchDeterministic:
    def test_returns_presentation_spec(self):
        spec = dispatch("meeting-notes-to-eos-rocks", "meeting notes", DETERMINISTIC)
        assert isinstance(spec, PresentationSpec)

    def test_all_playbooks_dispatch_deterministically(self):
        for pid in [
            "meeting-notes-to-eos-rocks",
            "ado-summary-to-weekly-delivery",
            "architecture-notes-to-adr-deck",
            "devops-metrics-to-scorecard",
            "generic-summary-playbook",
        ]:
            spec = dispatch(pid, "sample text", DETERMINISTIC)
            assert isinstance(spec, PresentationSpec)

    def test_deterministic_is_repeatable(self):
        text = "Sprint velocity dropped. Backlog has 14 blocked items."
        results = [dispatch("ado-summary-to-weekly-delivery", text, DETERMINISTIC) for _ in range(3)]
        titles = {r.title for r in results}
        assert len(titles) == 1


class TestDispatchAI:
    def test_returns_presentation_spec(self):
        spec = dispatch("meeting-notes-to-eos-rocks", "meeting notes action items", AI)
        assert isinstance(spec, PresentationSpec)

    def test_ai_is_repeatable(self):
        text = "Sprint velocity dropped. Backlog has 14 blocked items."
        results = [dispatch("ado-summary-to-weekly-delivery", text, AI) for _ in range(3)]
        titles = {r.title for r in results}
        assert len(titles) == 1


class TestDispatchErrors:
    def test_unknown_strategy_raises(self):
        with pytest.raises(UnknownStrategyError):
            dispatch("generic-summary-playbook", "text", "invalid-strategy")

    def test_error_message_lists_valid_strategies(self):
        with pytest.raises(UnknownStrategyError, match="deterministic"):
            dispatch("generic-summary-playbook", "text", "bad")
