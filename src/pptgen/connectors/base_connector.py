"""Connector contract — base types shared by all connectors.

Every connector transforms a local file into a
:class:`ConnectorOutput` containing:

- ``text``     — normalised, pipeline-ready text for
                 :func:`~pptgen.pipeline.generate_presentation`.
- ``metadata`` — optional structured data extracted from the source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass
class ConnectorOutput:
    """Result produced by any connector.

    Attributes:
        text:     Normalised text ready to be passed to the pptgen pipeline.
        metadata: Optional dict of structured fields extracted alongside the
                  text (e.g. sprint name, team, period).  May be empty.
    """

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Connector(Protocol):
    """Structural interface for all connector implementations.

    A connector reads a local source file and returns a
    :class:`ConnectorOutput`.  No network access is required or permitted.
    """

    def normalize(self, path: Path) -> ConnectorOutput:
        """Read *path* and return normalised pipeline-ready output.

        Args:
            path: Absolute or relative path to the source file.

        Returns:
            :class:`ConnectorOutput` with non-empty ``text``.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError:        If the file cannot be parsed.
        """
        ...  # pragma: no cover
