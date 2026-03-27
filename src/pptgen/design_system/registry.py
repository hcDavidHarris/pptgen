"""Design system registry — Phase 9 Stage 1 / Stage 2 / Stage 3 / Stage 4.

File-backed registry that discovers, validates, and loads design system
artifacts from the canonical directory layout::

    design_system/
      tokens/
        base_tokens.yaml
      brands/
        <brand_id>.yaml
      themes/
        <theme_id>.yaml
      layouts/
        <layout_id>.yaml
      primitives/
        <primitive_id>.yaml
      assets/
        <asset_id>.yaml   (e.g. icon.check.yaml)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .asset_models import VALID_ASSET_TYPES, AssetDefinition
from .exceptions import (
    DesignSystemSchemaError,
    InvalidAssetDefinitionError,
    InvalidAssetTypeError,
    InvalidLayoutDefinitionError,
    InvalidPrimitiveDefinitionError,
    UnknownAssetError,
    UnknownBrandError,
    UnknownLayoutError,
    UnknownPrimitiveError,
    UnknownThemeError,
)
from .layout_models import LayoutConstraints, LayoutDefinition, RegionDefinition
from .models import BaseTokenSet, BrandPack, ThemePack, TokenValue
from .primitive_models import (
    VALID_CONTENT_TYPES,
    PrimitiveConstraints,
    SlidePrimitiveDefinition,
    SlotDefinition,
)

# Required top-level keys per artifact type.
_BASE_TOKEN_KEYS = {"schema_version", "version", "tokens"}
_BRAND_KEYS = {"schema_version", "brand_id", "version", "token_overrides"}
_THEME_KEYS = {"schema_version", "theme_id", "version", "brand_id"}
_LAYOUT_KEYS = {"schema_version", "layout_id", "version", "regions"}
_PRIMITIVE_KEYS = {"schema_version", "primitive_id", "version", "layout_id", "slots"}
_ASSET_KEYS = {"schema_version", "asset_id", "version", "type", "source"}


class DesignSystemRegistry:
    """Loads and validates design system artifacts from a file system root.

    Args:
        design_system_path: Absolute or relative path to the ``design_system/``
            directory.  Must contain ``tokens/``, ``brands/``, and
            ``themes/`` subdirectories.

    Usage::

        registry = DesignSystemRegistry(Path("design_system"))
        base   = registry.load_base_tokens()
        brand  = registry.get_brand("healthcatalyst")
        theme  = registry.get_theme("executive")
    """

    def __init__(self, design_system_path: Path) -> None:
        self._root = Path(design_system_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_base_tokens(self) -> BaseTokenSet:
        """Load and return the base token set.

        Raises:
            DesignSystemSchemaError: If the file is missing, malformed, or
                fails schema validation.
        """
        path = self._root / "tokens" / "base_tokens.yaml"
        data = self._load_yaml(path)
        self._require_keys(data, _BASE_TOKEN_KEYS, path)
        tokens = data["tokens"]
        if not isinstance(tokens, dict):
            raise DesignSystemSchemaError(
                f"'tokens' in {path} must be a mapping, got {type(tokens).__name__}."
            )
        return BaseTokenSet(
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            tokens={k: _coerce_value(k, v) for k, v in tokens.items()},
        )

    def get_brand(self, brand_id: str) -> BrandPack:
        """Load a brand pack by ID.

        Args:
            brand_id: Stable brand identifier (filename stem under ``brands/``).

        Raises:
            UnknownBrandError: If no ``brands/<brand_id>.yaml`` exists.
            DesignSystemSchemaError: If the file is malformed.
        """
        path = self._root / "brands" / f"{brand_id}.yaml"
        if not path.exists():
            available = self.list_brands()
            raise UnknownBrandError(
                f"Brand '{brand_id}' not found. "
                f"Available: {', '.join(sorted(available)) or '(none)'}."
            )
        data = self._load_yaml(path)
        self._require_keys(data, _BRAND_KEYS, path)
        overrides = data["token_overrides"] or {}
        if not isinstance(overrides, dict):
            raise DesignSystemSchemaError(
                f"'token_overrides' in {path} must be a mapping, got {type(overrides).__name__}."
            )
        return BrandPack(
            brand_id=str(data["brand_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            token_overrides={k: _coerce_value(k, v) for k, v in overrides.items()},
        )

    def get_theme(self, theme_id: str) -> ThemePack:
        """Load a theme pack by ID.

        Supports ``theme_id@version`` syntax — the version suffix is parsed
        but currently used only for display; only one version per theme file
        is supported in Stage 1.

        Args:
            theme_id: Stable theme identifier, optionally suffixed with
                ``@<version>`` (e.g. ``"executive@v1"``).

        Raises:
            UnknownThemeError: If no ``themes/<theme_id>.yaml`` exists.
            DesignSystemSchemaError: If the file is malformed.
        """
        # Strip optional @version suffix for file lookup.
        stem = theme_id.split("@", 1)[0] if "@" in theme_id else theme_id

        path = self._root / "themes" / f"{stem}.yaml"
        if not path.exists():
            available = self.list_themes()
            raise UnknownThemeError(
                f"Theme '{stem}' not found. "
                f"Available: {', '.join(sorted(available)) or '(none)'}."
            )
        data = self._load_yaml(path)
        self._require_keys(data, _THEME_KEYS, path)
        overrides = data.get("token_overrides") or {}
        if not isinstance(overrides, dict):
            raise DesignSystemSchemaError(
                f"'token_overrides' in {path} must be a mapping, got {type(overrides).__name__}."
            )
        return ThemePack(
            theme_id=str(data["theme_id"]),
            version=str(data["version"]),
            brand_id=str(data["brand_id"]),
            schema_version=int(data["schema_version"]),
            token_overrides={k: _coerce_value(k, v) for k, v in overrides.items()},
        )

    def list_themes(self) -> list[str]:
        """Return a sorted list of registered theme IDs."""
        themes_dir = self._root / "themes"
        if not themes_dir.is_dir():
            return []
        return sorted(p.stem for p in themes_dir.glob("*.yaml"))

    def list_brands(self) -> list[str]:
        """Return a sorted list of registered brand IDs."""
        brands_dir = self._root / "brands"
        if not brands_dir.is_dir():
            return []
        return sorted(p.stem for p in brands_dir.glob("*.yaml"))

    def get_layout(self, layout_id: str) -> LayoutDefinition:
        """Load a layout definition by ID.

        Args:
            layout_id: Stable layout identifier (filename stem under ``layouts/``).

        Raises:
            UnknownLayoutError: If no ``layouts/<layout_id>.yaml`` exists.
            InvalidLayoutDefinitionError: If the file is malformed or fails
                schema validation.
        """
        path = self._root / "layouts" / f"{layout_id}.yaml"
        if not path.exists():
            available = self.list_layouts()
            raise UnknownLayoutError(
                f"Layout '{layout_id}' not found. "
                f"Available: {', '.join(sorted(available)) or '(none)'}."
            )
        try:
            data = self._load_yaml(path)
        except DesignSystemSchemaError as exc:
            raise InvalidLayoutDefinitionError(str(exc)) from exc

        missing = sorted(_LAYOUT_KEYS - set(data))
        if missing:
            raise InvalidLayoutDefinitionError(
                f"Missing required key(s) {missing} in {path}."
            )

        raw_regions = data["regions"]
        if not isinstance(raw_regions, dict):
            raise InvalidLayoutDefinitionError(
                f"'regions' in {path} must be a mapping, got {type(raw_regions).__name__}."
            )

        regions: dict[str, RegionDefinition] = {}
        for region_name, region_data in raw_regions.items():
            if not isinstance(region_data, dict):
                raise InvalidLayoutDefinitionError(
                    f"Region '{region_name}' in {path} must be a mapping."
                )
            regions[region_name] = RegionDefinition(
                name=region_name,
                required=bool(region_data.get("required", True)),
                label=str(region_data.get("label", "")),
                position=dict(region_data.get("position", {})),
            )

        raw_constraints = data.get("constraints") or {}
        if not isinstance(raw_constraints, dict):
            raise InvalidLayoutDefinitionError(
                f"'constraints' in {path} must be a mapping, got {type(raw_constraints).__name__}."
            )
        constraints = LayoutConstraints(
            allow_extra_slots=bool(raw_constraints.get("allow_extra_slots", False)),
        )

        return LayoutDefinition(
            layout_id=str(data["layout_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            regions=regions,
            constraints=constraints,
        )

    def list_layouts(self) -> list[str]:
        """Return a sorted list of registered layout IDs."""
        layouts_dir = self._root / "layouts"
        if not layouts_dir.is_dir():
            return []
        return sorted(p.stem for p in layouts_dir.glob("*.yaml"))

    def get_primitive(self, primitive_id: str) -> SlidePrimitiveDefinition:
        """Load a slide primitive definition by ID.

        Args:
            primitive_id: Stable primitive identifier (filename stem under
                ``primitives/``).

        Raises:
            UnknownPrimitiveError: If no ``primitives/<primitive_id>.yaml`` exists.
            InvalidPrimitiveDefinitionError: If the file is malformed or fails
                schema validation.
        """
        path = self._root / "primitives" / f"{primitive_id}.yaml"
        if not path.exists():
            available = self.list_primitives()
            raise UnknownPrimitiveError(
                f"Primitive '{primitive_id}' not found. "
                f"Available: {', '.join(sorted(available)) or '(none)'}."
            )
        try:
            data = self._load_yaml(path)
        except DesignSystemSchemaError as exc:
            raise InvalidPrimitiveDefinitionError(str(exc)) from exc

        missing = sorted(_PRIMITIVE_KEYS - set(data))
        if missing:
            raise InvalidPrimitiveDefinitionError(
                f"Missing required key(s) {missing} in {path}."
            )

        raw_slots = data["slots"]
        if not isinstance(raw_slots, dict):
            raise InvalidPrimitiveDefinitionError(
                f"'slots' in {path} must be a mapping, got {type(raw_slots).__name__}."
            )

        slots: dict[str, SlotDefinition] = {}
        for slot_name, slot_data in raw_slots.items():
            if not isinstance(slot_data, dict):
                raise InvalidPrimitiveDefinitionError(
                    f"Slot '{slot_name}' in {path} must be a mapping."
                )
            content_type = str(slot_data.get("content_type", "any"))
            if content_type not in VALID_CONTENT_TYPES:
                raise InvalidPrimitiveDefinitionError(
                    f"Slot '{slot_name}' in {path} has unknown content_type "
                    f"'{content_type}'. Valid types: {sorted(VALID_CONTENT_TYPES)}."
                )
            maps_to = str(slot_data.get("maps_to", slot_name))
            slots[slot_name] = SlotDefinition(
                name=slot_name,
                required=bool(slot_data.get("required", True)),
                content_type=content_type,
                maps_to=maps_to,
                description=str(slot_data.get("description", "")),
            )

        raw_constraints = data.get("constraints") or {}
        if not isinstance(raw_constraints, dict):
            raise InvalidPrimitiveDefinitionError(
                f"'constraints' in {path} must be a mapping, got "
                f"{type(raw_constraints).__name__}."
            )
        constraints = PrimitiveConstraints(
            allow_extra_content=bool(
                raw_constraints.get("allow_extra_content", False)
            ),
        )

        return SlidePrimitiveDefinition(
            primitive_id=str(data["primitive_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            layout_id=str(data["layout_id"]),
            slots=slots,
            constraints=constraints,
        )

    def list_primitives(self) -> list[str]:
        """Return a sorted list of registered primitive IDs."""
        primitives_dir = self._root / "primitives"
        if not primitives_dir.is_dir():
            return []
        return sorted(p.stem for p in primitives_dir.glob("*.yaml"))

    def get_asset(self, asset_id: str) -> AssetDefinition:
        """Load an asset definition by ID.

        Args:
            asset_id: Dot-separated asset identifier — must match a filename
                stem under ``assets/`` (e.g. ``"icon.check"`` →
                ``assets/icon.check.yaml``).

        Raises:
            UnknownAssetError: If no ``assets/<asset_id>.yaml`` exists.
            InvalidAssetDefinitionError: If the file is malformed or fails
                schema validation.
            InvalidAssetTypeError: If the ``type`` field is not a recognised
                asset type.
        """
        path = self._root / "assets" / f"{asset_id}.yaml"
        if not path.exists():
            available = self.list_assets()
            raise UnknownAssetError(
                f"Asset '{asset_id}' not found. "
                f"Available: {', '.join(sorted(available)) or '(none)'}."
            )
        try:
            data = self._load_yaml(path)
        except DesignSystemSchemaError as exc:
            raise InvalidAssetDefinitionError(str(exc)) from exc

        missing = sorted(_ASSET_KEYS - set(data))
        if missing:
            raise InvalidAssetDefinitionError(
                f"Missing required key(s) {missing} in {path}."
            )

        asset_type = str(data["type"])
        if asset_type not in VALID_ASSET_TYPES:
            raise InvalidAssetTypeError(
                f"Asset '{asset_id}' in {path} declares unsupported type "
                f"'{asset_type}'. Valid types: {sorted(VALID_ASSET_TYPES)}."
            )

        raw_metadata = data.get("metadata") or {}
        if not isinstance(raw_metadata, dict):
            raise InvalidAssetDefinitionError(
                f"'metadata' in {path} must be a mapping, got "
                f"{type(raw_metadata).__name__}."
            )

        return AssetDefinition(
            asset_id=str(data["asset_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            type=asset_type,
            source=str(data["source"]),
            metadata=dict(raw_metadata),
        )

    def list_assets(self) -> list[str]:
        """Return a sorted list of registered asset IDs."""
        assets_dir = self._root / "assets"
        if not assets_dir.is_dir():
            return []
        return sorted(p.stem for p in assets_dir.glob("*.yaml"))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        try:
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except FileNotFoundError:
            raise DesignSystemSchemaError(
                f"Design system file not found: {path}"
            )
        except yaml.YAMLError as exc:
            raise DesignSystemSchemaError(
                f"YAML parse error in {path}: {exc}"
            )
        if not isinstance(data, dict):
            raise DesignSystemSchemaError(
                f"Expected a YAML mapping in {path}, got {type(data).__name__}."
            )
        return data

    @staticmethod
    def _require_keys(
        data: dict[str, Any],
        required: set[str],
        source: Path,
    ) -> None:
        missing = sorted(required - set(data))
        if missing:
            raise DesignSystemSchemaError(
                f"Missing required key(s) {missing} in {source}."
            )


def _coerce_value(key: str, value: Any) -> TokenValue:
    """Ensure token values are str, int, or float; raise on unsupported types."""
    if isinstance(value, (str, int, float)):
        return value
    if isinstance(value, bool):
        # YAML parses `true`/`false` as bool; treat as string.
        return str(value).lower()
    raise DesignSystemSchemaError(
        f"Token '{key}' has unsupported value type {type(value).__name__!r}. "
        f"Token values must be str, int, or float."
    )
