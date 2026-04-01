"""Asset models for the pptgen design system — Phase 9 Stage 4.

Two flat artifacts:

* :class:`AssetDefinition`  — a config artifact loaded from a YAML file in
  ``design_system/assets/``.
* :class:`ResolvedAsset`    — the concrete asset produced by
  :class:`~.asset_resolver.AssetResolver` when it replaces an ``asset_id``
  reference in deck content.

Assets are *references*, not payloads.  The resolver replaces a reference dict
such as ``{"asset_id": "icon.check"}`` with the resolved metadata dict in-place
inside the deck definition.  The renderer treats this dict as an opaque input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Valid asset type identifiers.
VALID_ASSET_TYPES = frozenset({"icon", "image", "logo"})

#: The key that marks a dict as an asset reference inside deck content.
ASSET_REF_KEY = "asset_id"


@dataclass(frozen=True)
class AssetDefinition:
    """A reusable visual resource defined in a YAML config artifact.

    Attributes:
        asset_id:       Stable dot-separated identifier (e.g. ``"icon.check"``).
                        Matches the filename stem under ``design_system/assets/``.
        version:        Artifact version string (e.g. ``"1.0.0"``).
        schema_version: Configuration schema version (integer).
        type:           Asset category — one of ``"icon"``, ``"image"``,
                        ``"logo"``.
        source:         Path or URI pointing to the asset file.  Treated as
                        opaque by the platform; the renderer is responsible for
                        resolving it relative to its own working directory.
        metadata:       Optional extra key/value pairs (alt text, description,
                        dimensions, etc.).
    """

    asset_id: str
    version: str
    schema_version: int
    type: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedAsset:
    """A concrete asset produced when an ``asset_id`` reference is resolved.

    Instances are collected into a list and stored in
    ``PipelineResult.resolved_assets`` for auditability.  They are also
    embedded back into the deck definition in place of the original reference
    dict so the renderer receives them directly.

    Attributes:
        asset_id:         The ID that was referenced.
        version:          Version of the matched :class:`AssetDefinition`.
        type:             Asset category (``"icon"``, ``"image"``, ``"logo"``).
        resolved_source:  Source string from the :class:`AssetDefinition`.
    """

    asset_id: str
    version: str
    type: str
    resolved_source: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON persistence."""
        return {
            "asset_id": self.asset_id,
            "version": self.version,
            "type": self.type,
            "resolved_source": self.resolved_source,
        }

    def as_inline(self) -> dict[str, Any]:
        """Return the dict that replaces the original reference in deck content.

        Keeps ``asset_id`` so the provenance is traceable in the rendered
        output, and adds resolved metadata.
        """
        return {
            "asset_id": self.asset_id,
            "resolved_source": self.resolved_source,
            "type": self.type,
            "version": self.version,
        }
