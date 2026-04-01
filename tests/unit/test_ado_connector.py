"""Unit tests for the ADO connector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptgen.connectors import ConnectorOutput
from pptgen.connectors.ado_connector import ADOConnector
from pptgen.input_router import route_input


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_SPRINT_EXPORT = _FIXTURES / "sprint_export.json"


class TestADOConnectorBasics:
    def test_returns_connector_output(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert isinstance(out, ConnectorOutput)

    def test_text_is_non_empty(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert out.text.strip()

    def test_metadata_is_dict(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert isinstance(out.metadata, dict)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ADOConnector().normalize(tmp_path / "no_such_file.json")

    def test_malformed_json_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ not valid json", encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot parse ADO JSON"):
            ADOConnector().normalize(bad)


class TestADONormalization:
    def test_sprint_name_in_text(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "Sprint" in out.text

    def test_velocity_in_text(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "velocity" in out.text.lower() or "Velocity" in out.text

    def test_story_points_in_text(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "story points" in out.text.lower()

    def test_blocked_in_text(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "blocked" in out.text.lower()

    def test_work_items_in_text(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "work items" in out.text.lower() or "Work items" in out.text

    def test_work_item_titles_in_text(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "OAuth" in out.text or "login" in out.text.lower()

    def test_metadata_contains_sprint(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "sprint" in out.metadata

    def test_metadata_contains_velocity(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert "velocity" in out.metadata
        assert out.metadata["velocity"] == 38

    def test_deterministic(self):
        c = ADOConnector()
        out1 = c.normalize(_SPRINT_EXPORT)
        out2 = c.normalize(_SPRINT_EXPORT)
        assert out1.text == out2.text


class TestADOConnectorEmptyData:
    def test_empty_json_object_produces_output(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}", encoding="utf-8")
        out = ADOConnector().normalize(p)
        assert isinstance(out, ConnectorOutput)

    def test_minimal_sprint_fields(self, tmp_path):
        p = tmp_path / "min.json"
        p.write_text(json.dumps({"sprint": "Sprint 1", "velocity": 10}), encoding="utf-8")
        out = ADOConnector().normalize(p)
        assert "Sprint 1" in out.text
        assert "10" in out.text


class TestADORouting:
    def test_routes_to_ado_delivery(self):
        out = ADOConnector().normalize(_SPRINT_EXPORT)
        assert route_input(out.text) == "ado-summary-to-weekly-delivery"
