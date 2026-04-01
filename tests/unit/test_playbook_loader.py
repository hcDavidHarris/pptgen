"""Unit tests for the playbook loader."""

from __future__ import annotations

import pytest

from pptgen.input_router.routing_table_loader import RouteEntry
from pptgen.playbook_engine.playbook_loader import (
    PlaybookNotFoundError,
    load_playbook,
)


class TestLoadPlaybookKnownIds:
    def test_meeting_notes_resolves(self):
        entry = load_playbook("meeting-notes-to-eos-rocks")
        assert entry is not None
        assert isinstance(entry, RouteEntry)

    def test_ado_summary_resolves(self):
        entry = load_playbook("ado-summary-to-weekly-delivery")
        assert entry is not None

    def test_architecture_notes_resolves(self):
        entry = load_playbook("architecture-notes-to-adr-deck")
        assert entry is not None

    def test_devops_metrics_resolves(self):
        entry = load_playbook("devops-metrics-to-scorecard")
        assert entry is not None

    def test_resolved_entry_has_playbook_id(self):
        entry = load_playbook("meeting-notes-to-eos-rocks")
        assert entry.playbook_id == "meeting-notes-to-eos-rocks"

    def test_resolved_entry_has_example_pattern(self):
        entry = load_playbook("ado-summary-to-weekly-delivery")
        assert entry.example_pattern
        assert "yaml" in entry.example_pattern

    def test_resolved_entry_has_playbook_path(self):
        entry = load_playbook("architecture-notes-to-adr-deck")
        assert entry.playbook_path
        assert entry.playbook_path.endswith(".md")


class TestLoadPlaybookGenericFallback:
    def test_generic_returns_none(self):
        result = load_playbook("generic-summary-playbook")
        assert result is None

    def test_generic_does_not_raise(self):
        # Must not raise PlaybookNotFoundError
        load_playbook("generic-summary-playbook")


class TestLoadPlaybookUnknownId:
    def test_unknown_id_raises(self):
        with pytest.raises(PlaybookNotFoundError):
            load_playbook("totally-unknown-playbook")

    def test_error_message_includes_id(self):
        with pytest.raises(PlaybookNotFoundError, match="nonexistent-id"):
            load_playbook("nonexistent-id")

    def test_error_message_suggests_generic(self):
        with pytest.raises(PlaybookNotFoundError, match="generic-summary-playbook"):
            load_playbook("bad-id")
