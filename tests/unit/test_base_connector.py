"""Unit tests for the connector contract (ConnectorOutput and Connector protocol)."""

from __future__ import annotations

from pathlib import Path

from pptgen.connectors import Connector, ConnectorOutput


class TestConnectorOutput:
    def test_instantiation(self):
        out = ConnectorOutput(text="hello")
        assert out is not None

    def test_text_field(self):
        out = ConnectorOutput(text="some text")
        assert out.text == "some text"

    def test_metadata_defaults_to_empty_dict(self):
        out = ConnectorOutput(text="hello")
        assert out.metadata == {}

    def test_metadata_accepts_values(self):
        out = ConnectorOutput(text="hello", metadata={"key": "value"})
        assert out.metadata["key"] == "value"

    def test_text_can_be_empty_string(self):
        out = ConnectorOutput(text="")
        assert out.text == ""

    def test_metadata_can_hold_mixed_types(self):
        out = ConnectorOutput(text="x", metadata={"a": 1, "b": ["x", "y"], "c": None})
        assert out.metadata["a"] == 1
        assert out.metadata["b"] == ["x", "y"]


class TestConnectorProtocol:
    def test_protocol_exists(self):
        assert Connector is not None

    def test_object_with_normalize_satisfies_protocol(self):
        class MinimalConnector:
            def normalize(self, path: Path) -> ConnectorOutput:
                return ConnectorOutput(text="ok")

        assert isinstance(MinimalConnector(), Connector)

    def test_object_without_normalize_fails_protocol(self):
        class NoNormalize:
            pass

        assert not isinstance(NoNormalize(), Connector)
