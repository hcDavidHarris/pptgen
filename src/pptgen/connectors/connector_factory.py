"""Connector factory — resolves connector type strings to instances.

Supported connector types::

    "transcript"  ->  TranscriptConnector
    "ado"         ->  ADOConnector
    "metrics"     ->  MetricsConnector
"""

from __future__ import annotations

from .ado_connector import ADOConnector
from .base_connector import Connector
from .metrics_connector import MetricsConnector
from .transcript_connector import TranscriptConnector


#: Mapping of connector type name to class.
_REGISTRY: dict[str, type] = {
    "transcript": TranscriptConnector,
    "ado": ADOConnector,
    "metrics": MetricsConnector,
}

#: Frozenset of all supported connector type names.
SUPPORTED_CONNECTORS: frozenset[str] = frozenset(_REGISTRY)


class UnknownConnectorError(ValueError):
    """Raised when an unrecognised connector type is requested."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.CONFIGURATION


def get_connector(connector_type: str) -> Connector:
    """Return a connector instance for *connector_type*.

    Args:
        connector_type: One of ``"transcript"``, ``"ado"``, ``"metrics"``.

    Returns:
        A :class:`~pptgen.connectors.base_connector.Connector` instance.

    Raises:
        UnknownConnectorError: If *connector_type* is not supported.
    """
    cls = _REGISTRY.get(connector_type)
    if cls is None:
        supported = ", ".join(sorted(SUPPORTED_CONNECTORS))
        raise UnknownConnectorError(
            f"Unknown connector type '{connector_type}'.  "
            f"Supported types: {supported}."
        )
    return cls()
