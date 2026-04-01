"""Token resolver — Phase 9 Stage 1.

Applies the three-layer precedence model::

    Base Tokens → Brand Pack Overrides → Theme Pack Overrides → ResolvedStyleMap

Also handles ``token.<key>`` reference substitution in deck definition dicts.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .exceptions import InvalidTokenOverrideError, UnknownTokenError
from .models import BaseTokenSet, BrandPack, ResolvedStyleMap, ThemePack, TokenValue

# Matches values of the form "token.color.primary", "token.font.size.title", etc.
_TOKEN_REF_RE = re.compile(r"^token\.(.+)$")


class TokenResolver:
    """Applies the design system precedence model and resolves token references.

    Usage::

        resolver = TokenResolver()
        style_map = resolver.resolve(base_tokens, brand_pack, theme_pack)
        resolved_deck = resolver.resolve_references(deck_definition, style_map)
    """

    def resolve(
        self,
        base: BaseTokenSet,
        brand: BrandPack,
        theme: ThemePack,
    ) -> ResolvedStyleMap:
        """Produce a :class:`~.models.ResolvedStyleMap` from three config layers.

        Applies precedence: base → brand overrides → theme overrides.

        Args:
            base:  The canonical base token set.
            brand: Brand pack whose overrides are applied first.
            theme: Theme pack whose overrides are applied last.

        Returns:
            Fully resolved :class:`~.models.ResolvedStyleMap`.

        Raises:
            InvalidTokenOverrideError: If brand or theme attempts to override
                a token key not present in *base*.
        """
        self._validate_overrides(base, brand.token_overrides, f"Brand '{brand.brand_id}'")
        self._validate_overrides(base, theme.token_overrides, f"Theme '{theme.theme_id}'")

        resolved: dict[str, TokenValue] = {}
        resolved.update(base.tokens)
        resolved.update(brand.token_overrides)
        resolved.update(theme.token_overrides)

        return ResolvedStyleMap(
            theme_id=theme.theme_id,
            theme_version=theme.version,
            brand_id=brand.brand_id,
            brand_version=brand.version,
            token_set_version=base.version,
            resolved_at=datetime.now(tz=timezone.utc).isoformat(),
            tokens=resolved,
        )

    def resolve_references(
        self,
        deck_definition: dict[str, Any],
        style_map: ResolvedStyleMap,
    ) -> dict[str, Any]:
        """Substitute ``token.<key>`` references inside a deck definition.

        Recursively walks the dict/list structure and replaces any string
        value matching ``token.<key>`` with the concrete value from
        *style_map*.

        Args:
            deck_definition: Plain dict representation of a DeckFile.
            style_map:       Resolved style map to substitute from.

        Returns:
            New dict with all token references replaced.

        Raises:
            UnknownTokenError: If any ``token.<key>`` reference does not
                appear in *style_map*.
        """
        return _walk(deck_definition, style_map)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_overrides(
        base: BaseTokenSet,
        overrides: dict[str, TokenValue],
        source_label: str,
    ) -> None:
        unknown = sorted(set(overrides) - set(base.tokens))
        if unknown:
            valid = sorted(base.tokens)
            raise InvalidTokenOverrideError(
                f"{source_label} overrides unknown token(s): "
                f"{', '.join(unknown)}. "
                f"Valid token keys: {', '.join(valid)}."
            )


def _walk(obj: Any, style_map: ResolvedStyleMap) -> Any:
    """Recursively substitute token references in *obj*."""
    if isinstance(obj, dict):
        return {k: _walk(v, style_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_walk(item, style_map) for item in obj]
    if isinstance(obj, str):
        m = _TOKEN_REF_RE.match(obj)
        if m:
            key = m.group(1)
            if key not in style_map.tokens:
                available = ", ".join(sorted(style_map.tokens))
                raise UnknownTokenError(
                    f"Unknown design token reference 'token.{key}'. "
                    f"Available tokens: {available}."
                )
            return style_map.tokens[key]
    return obj
