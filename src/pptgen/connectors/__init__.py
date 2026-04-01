"""pptgen input connectors — Phase 5D.

Connectors transform structured source files into normalised text suitable
for the pptgen generation pipeline.

Public API::

    from pptgen.connectors import ConnectorOutput, get_connector, SUPPORTED_CONNECTORS

    connector = get_connector("transcript")
    output = connector.normalize(Path("notes.txt"))
    result = generate_presentation(output.text)
"""

from .base_connector import Connector, ConnectorOutput
from .connector_factory import SUPPORTED_CONNECTORS, UnknownConnectorError, get_connector

__all__ = [
    "Connector",
    "ConnectorOutput",
    "get_connector",
    "SUPPORTED_CONNECTORS",
    "UnknownConnectorError",
]
