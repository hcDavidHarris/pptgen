"""Unit tests for the routing table loader."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from pptgen.input_router.routing_table_loader import (
    RouteEntry,
    RoutingTableError,
    load_routing_table,
)


_PROJECT_ROOT = Path(__file__).parent.parent.parent
_REAL_TABLE = _PROJECT_ROOT / "docs" / "ai-playbooks" / "routing_table.yaml"


# ---------------------------------------------------------------------------
# Loading the real routing table
# ---------------------------------------------------------------------------

class TestLoadRealRoutingTable:
    def test_loads_without_error(self):
        entries = load_routing_table()
        assert isinstance(entries, list)

    def test_returns_route_entries(self):
        entries = load_routing_table()
        assert all(isinstance(e, RouteEntry) for e in entries)

    def test_expected_route_count(self):
        entries = load_routing_table()
        assert len(entries) == 4

    def test_expected_route_ids_present(self):
        ids = {e.route_id for e in load_routing_table()}
        assert "meeting_notes_to_eos_rocks" in ids
        assert "ado_summary_to_weekly_delivery" in ids
        assert "architecture_notes_to_adr_deck" in ids
        assert "devops_metrics_to_scorecard" in ids

    def test_playbook_ids_are_hyphenated(self):
        """playbook_id must be derived from the filename, not route_id."""
        ids = {e.playbook_id for e in load_routing_table()}
        assert "meeting-notes-to-eos-rocks" in ids
        assert "ado-summary-to-weekly-delivery" in ids
        assert "architecture-notes-to-adr-deck" in ids
        assert "devops-metrics-to-scorecard" in ids

    def test_input_types_are_tuples(self):
        for entry in load_routing_table():
            assert isinstance(entry.input_types, tuple)

    def test_tags_are_tuples(self):
        for entry in load_routing_table():
            assert isinstance(entry.tags, tuple)

    def test_example_pattern_non_empty(self):
        for entry in load_routing_table():
            assert entry.example_pattern, f"Empty example_pattern on {entry.route_id}"

    def test_meeting_notes_entry_details(self):
        entry = next(
            e for e in load_routing_table()
            if e.route_id == "meeting_notes_to_eos_rocks"
        )
        assert entry.playbook_id == "meeting-notes-to-eos-rocks"
        assert "meeting_notes" in entry.input_types
        assert "eos" in entry.tags
        assert "eos_rocks" in entry.example_pattern


# ---------------------------------------------------------------------------
# Error conditions (using tmp_path / synthetic files)
# ---------------------------------------------------------------------------

class TestRoutingTableErrors:
    def test_missing_file_raises_routing_table_error(self, tmp_path):
        with pytest.raises(RoutingTableError, match="not found"):
            load_routing_table(tmp_path / "nonexistent.yaml")

    def test_malformed_yaml_raises_routing_table_error(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("routes: [invalid: yaml: :::\n", encoding="utf-8")
        with pytest.raises(RoutingTableError):
            load_routing_table(bad)

    def test_missing_routes_key_raises_routing_table_error(self, tmp_path):
        bad = tmp_path / "no_routes.yaml"
        bad.write_text("something_else:\n  - id: foo\n", encoding="utf-8")
        with pytest.raises(RoutingTableError, match="'routes'"):
            load_routing_table(bad)

    def test_route_missing_required_field_raises(self, tmp_path):
        bad = tmp_path / "missing_field.yaml"
        # 'playbook' is required; omit it
        data = {"routes": [{"route_id": "r1", "description": "d"}]}
        bad.write_text(yaml.dump(data), encoding="utf-8")
        with pytest.raises(RoutingTableError, match="Malformed route"):
            load_routing_table(bad)

    def test_empty_routes_list_is_valid(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("routes: []\n", encoding="utf-8")
        entries = load_routing_table(f)
        assert entries == []
