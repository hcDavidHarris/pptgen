"""Unit tests for the execution strategy dispatcher."""

from __future__ import annotations

import pytest

from pptgen.playbook_engine.execution_strategy import (
    AI,
    DETERMINISTIC,
    VALID_STRATEGIES,
    UnknownStrategyError,
    dispatch,
)
from pptgen.spec.presentation_spec import PresentationSpec


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
