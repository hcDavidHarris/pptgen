"""Unit tests for the metrics connector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pptgen.connectors import ConnectorOutput
from pptgen.connectors.metrics_connector import MetricsConnector
from pptgen.input_router import route_input


_FIXTURES = Path(__file__).parent.parent / "fixtures"
_METRICS = _FIXTURES / "devops_metrics.json"


class TestMetricsConnectorBasics:
    def test_returns_connector_output(self):
        out = MetricsConnector().normalize(_METRICS)
        assert isinstance(out, ConnectorOutput)

    def test_text_is_non_empty(self):
        out = MetricsConnector().normalize(_METRICS)
        assert out.text.strip()

    def test_metadata_is_dict(self):
        out = MetricsConnector().normalize(_METRICS)
        assert isinstance(out.metadata, dict)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            MetricsConnector().normalize(tmp_path / "no_such.json")

    def test_malformed_json_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json at all", encoding="utf-8")
        with pytest.raises(ValueError, match="Cannot parse metrics JSON"):
            MetricsConnector().normalize(bad)


class TestMetricsNormalization:
    def test_dora_term_in_text(self):
        out = MetricsConnector().normalize(_METRICS)
        assert "DORA" in out.text or "dora" in out.text.lower()

    def test_deployment_frequency_in_text(self):
        out = MetricsConnector().normalize(_METRICS)
        assert "deployment frequency" in out.text.lower()

    def test_change_failure_rate_in_text(self):
        out = MetricsConnector().normalize(_METRICS)
        assert "change failure rate" in out.text.lower()

    def test_mttr_in_text(self):
        out = MetricsConnector().normalize(_METRICS)
        assert "mttr" in out.text.lower() or "mean time to restore" in out.text.lower()

    def test_metric_values_in_text(self):
        out = MetricsConnector().normalize(_METRICS)
        # Values from the fixture
        assert "4 per day" in out.text
        assert "1.8%" in out.text
        assert "12 minutes" in out.text

    def test_metadata_contains_deployment_frequency(self):
        out = MetricsConnector().normalize(_METRICS)
        assert "deployment_frequency" in out.metadata

    def test_metadata_contains_team(self):
        out = MetricsConnector().normalize(_METRICS)
        assert "team" in out.metadata

    def test_deterministic(self):
        c = MetricsConnector()
        out1 = c.normalize(_METRICS)
        out2 = c.normalize(_METRICS)
        assert out1.text == out2.text


class TestMetricsConnectorEmptyData:
    def test_empty_json_object_produces_output(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}", encoding="utf-8")
        out = MetricsConnector().normalize(p)
        assert isinstance(out, ConnectorOutput)

    def test_minimal_dora_fields(self, tmp_path):
        p = tmp_path / "min.json"
        data = {"dora_metrics": {"deployment_frequency": "2/day", "mttr": "30 minutes"}}
        p.write_text(json.dumps(data), encoding="utf-8")
        out = MetricsConnector().normalize(p)
        assert "2/day" in out.text
        assert "30 minutes" in out.text


class TestMetricsRouting:
    def test_routes_to_devops_scorecard(self):
        out = MetricsConnector().normalize(_METRICS)
        assert route_input(out.text) == "devops-metrics-to-scorecard"
