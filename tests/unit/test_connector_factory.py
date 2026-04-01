"""Unit tests for the connector factory."""

from __future__ import annotations

import pytest

from pptgen.connectors import SUPPORTED_CONNECTORS, UnknownConnectorError, get_connector
from pptgen.connectors.ado_connector import ADOConnector
from pptgen.connectors.base_connector import Connector
from pptgen.connectors.metrics_connector import MetricsConnector
from pptgen.connectors.transcript_connector import TranscriptConnector


class TestSupportedConnectors:
    def test_transcript_supported(self):
        assert "transcript" in SUPPORTED_CONNECTORS

    def test_ado_supported(self):
        assert "ado" in SUPPORTED_CONNECTORS

    def test_metrics_supported(self):
        assert "metrics" in SUPPORTED_CONNECTORS

    def test_is_frozenset(self):
        assert isinstance(SUPPORTED_CONNECTORS, frozenset)

    def test_exactly_three_connectors(self):
        assert len(SUPPORTED_CONNECTORS) == 3


class TestGetConnector:
    def test_transcript_returns_transcript_connector(self):
        assert isinstance(get_connector("transcript"), TranscriptConnector)

    def test_ado_returns_ado_connector(self):
        assert isinstance(get_connector("ado"), ADOConnector)

    def test_metrics_returns_metrics_connector(self):
        assert isinstance(get_connector("metrics"), MetricsConnector)

    def test_all_return_connector_instances(self):
        for ctype in SUPPORTED_CONNECTORS:
            c = get_connector(ctype)
            assert isinstance(c, Connector)

    def test_unknown_type_raises(self):
        with pytest.raises(UnknownConnectorError):
            get_connector("unknown-connector")

    def test_error_message_lists_supported(self):
        with pytest.raises(UnknownConnectorError, match="transcript"):
            get_connector("bad-type")

    def test_empty_string_raises(self):
        with pytest.raises(UnknownConnectorError):
            get_connector("")

    def test_each_call_returns_fresh_instance(self):
        c1 = get_connector("transcript")
        c2 = get_connector("transcript")
        assert c1 is not c2
