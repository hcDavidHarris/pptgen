"""Domain models for the pptgen design system — Phase 9 Stage 1.

Four first-class artifacts:

* :class:`BaseTokenSet` — canonical semantic token vocabulary with default values.
* :class:`BrandPack` — organization-specific token overrides.
* :class:`ThemePack` — presentation-level token overrides that reference a brand.
* :class:`ResolvedStyleMap` — fully resolved token map produced by :class:`~.token_resolver.TokenResolver`.

Token values are scalar: ``str`` for colors and font families, ``int | float`` for
sizes and spacing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Type alias for a scalar token value.
TokenValue = str | int | float


@dataclass(frozen=True)
class BaseTokenSet:
    """Canonical design vocabulary.

    Defines every valid token key and its default value.  Brand and theme
    packs may only override keys present in this set.

    Attributes:
        version:        Artifact version string (e.g. ``"1.0.0"``).
        schema_version: Configuration schema version (integer).
        tokens:         Mapping of token key → default value.
    """

    version: str
    schema_version: int
    tokens: dict[str, TokenValue]


@dataclass(frozen=True)
class BrandPack:
    """Organization-specific visual identity overrides.

    Attributes:
        brand_id:        Stable identifier (e.g. ``"healthcatalyst"``).
        version:         Artifact version string.
        schema_version:  Configuration schema version.
        token_overrides: Subset of base token keys mapped to brand values.
                         May not introduce new keys.
    """

    brand_id: str
    version: str
    schema_version: int
    token_overrides: dict[str, TokenValue]


@dataclass(frozen=True)
class ThemePack:
    """Presentation-level styling choices.

    Themes reference a brand pack and optionally narrow token values further
    for a specific presentation style (e.g. executive, technical).

    Attributes:
        theme_id:        Stable identifier (e.g. ``"executive"``).
        version:         Artifact version string.
        brand_id:        Brand pack this theme is based on.
        schema_version:  Configuration schema version.
        token_overrides: Further token overrides on top of the brand layer.
                         May not introduce new keys.
    """

    theme_id: str
    version: str
    brand_id: str
    schema_version: int
    token_overrides: dict[str, TokenValue]


@dataclass(frozen=True)
class ResolvedStyleMap:
    """Fully resolved token map produced by the :class:`~.token_resolver.TokenResolver`.

    This is the concrete styling contract delivered to the rendering engine.
    One instance is created per run and persisted as
    ``resolved_theme_snapshot.json`` for auditability and reproducibility.

    Attributes:
        theme_id:          Theme used in resolution.
        theme_version:     Version of that theme.
        brand_id:          Brand applied beneath the theme.
        brand_version:     Version of that brand.
        token_set_version: Version of the base token set.
        resolved_at:       ISO 8601 UTC timestamp of resolution.
        tokens:            Fully resolved ``{token_key: concrete_value}`` map.
    """

    theme_id: str
    theme_version: str
    brand_id: str
    brand_version: str
    token_set_version: str
    resolved_at: str
    tokens: dict[str, TokenValue]

    def get(self, key: str, default: TokenValue | None = None) -> TokenValue | None:
        """Return the resolved value for *key*, or *default* if absent."""
        return self.tokens.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict suitable for JSON persistence."""
        return {
            "theme_id": self.theme_id,
            "theme_version": self.theme_version,
            "brand_id": self.brand_id,
            "brand_version": self.brand_version,
            "token_set_version": self.token_set_version,
            "resolved_at": self.resolved_at,
            "tokens": dict(self.tokens),
        }
