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

Phase 10A adds optional governance and family metadata parsing — strictly
additive; no existing getter return types or resolution behavior is changed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .asset_models import VALID_ASSET_TYPES, AssetDefinition
from .exceptions import (
    DesignSystemSchemaError,
    GovernanceViolationError,
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
from .governance_models import (
    GovernedArtifactFamily,
    GovernedArtifactVersion,
    LifecycleStatus,
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

# Canonical artifact_type values used throughout governance code.
_ARTIFACT_TYPE_TOKEN_SET = "token_set"
_ARTIFACT_TYPE_THEME     = "theme"
_ARTIFACT_TYPE_LAYOUT    = "layout"
_ARTIFACT_TYPE_PRIMITIVE = "primitive"
_ARTIFACT_TYPE_ASSET     = "asset"

# Maps canonical artifact_type → subdirectory name under design_system root.
_ARTIFACT_SUBDIR: dict[str, str] = {
    _ARTIFACT_TYPE_TOKEN_SET: "tokens",
    _ARTIFACT_TYPE_THEME:     "themes",
    _ARTIFACT_TYPE_LAYOUT:    "layouts",
    _ARTIFACT_TYPE_PRIMITIVE: "primitives",
    _ARTIFACT_TYPE_ASSET:     "assets",
}

# Implicit artifact_id used for the singleton base token set.
_BASE_TOKEN_ARTIFACT_ID = "base"


# ---------------------------------------------------------------------------
# Governance parsing helpers (module-level, no side-effects)
# ---------------------------------------------------------------------------

def _parse_gov_datetime(raw: Any) -> datetime | None:
    """Safely parse a datetime field from a governance block.

    PyYAML may return the value as a native ``datetime`` (when written as a
    bare YAML timestamp) or as a string (when quoted).  Both are handled.
    Absent fields (``None``) are returned unchanged.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        try:
            # Normalise UTC "Z" suffix for datetime.fromisoformat compatibility
            # across Python versions (< 3.11 does not accept "Z").
            normalized = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _parse_lifecycle(raw: Any, source: Path) -> LifecycleStatus:
    """Parse and validate a governance status string.

    Defaults to ``APPROVED`` when the field is absent.

    Raises:
        DesignSystemSchemaError: If the value is present but not a valid
            :class:`~.governance_models.LifecycleStatus` member.
    """
    if raw is None:
        return LifecycleStatus.APPROVED
    try:
        return LifecycleStatus(str(raw).lower())
    except ValueError:
        valid = sorted(s.value for s in LifecycleStatus)
        raise DesignSystemSchemaError(
            f"Invalid governance status {raw!r} in {source}. "
            f"Valid values: {valid}."
        )


def _parse_governance_block(
    data: dict[str, Any],
    artifact_type: str,
    artifact_id: str,
    version: str,
    source: Path,
) -> tuple[GovernedArtifactVersion, GovernedArtifactFamily]:
    """Parse optional ``governance:`` and ``family:`` blocks from artifact YAML.

    Both blocks are optional.  When absent:
    - governance defaults to ``lifecycle_status=APPROVED``, all audit fields ``None``
    - family defaults to ``default_version=None``

    Returns a ``(GovernedArtifactVersion, GovernedArtifactFamily)`` pair.
    A family object is always returned so callers never need to guard for None.

    Raises:
        DesignSystemSchemaError: If ``governance.status`` is not a valid
            :class:`~.governance_models.LifecycleStatus`.
    """
    raw_gov: dict[str, Any] = data.get("governance") or {}

    gov = GovernedArtifactVersion(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        version=version,
        lifecycle_status=_parse_lifecycle(raw_gov.get("status"), source),
        created_at=_parse_gov_datetime(raw_gov.get("created_at")),
        created_by=raw_gov.get("created_by") or None,
        promoted_at=_parse_gov_datetime(raw_gov.get("promoted_at")),
        promoted_by=raw_gov.get("promoted_by") or None,
        deprecated_at=_parse_gov_datetime(raw_gov.get("deprecated_at")),
        deprecated_by=raw_gov.get("deprecated_by") or None,
        deprecation_reason=raw_gov.get("deprecation_reason") or None,
    )

    raw_family: dict[str, Any] = data.get("family") or {}
    raw_default = raw_family.get("default_version")
    family = GovernedArtifactFamily(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        default_version=str(raw_default) if raw_default is not None else None,
    )

    return gov, family


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
        # Parallel governance indexes — populated lazily via _ensure_gov_loaded().
        # Keys: (artifact_type, artifact_id, version) for versions,
        #        (artifact_type, artifact_id)          for families.
        # These indexes are additive; no existing getter return type changes.
        self._gov_versions: dict[tuple[str, str, str], GovernedArtifactVersion] = {}
        self._gov_families: dict[tuple[str, str], GovernedArtifactFamily] = {}
        # Tracks (artifact_type, artifact_id) pairs already loaded into the
        # governance indexes so we do not re-parse on repeated calls.
        self._gov_loaded: set[tuple[str, str]] = set()

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
        result = BaseTokenSet(
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            tokens={k: _coerce_value(k, v) for k, v in tokens.items()},
        )
        self._ensure_gov_loaded(
            _ARTIFACT_TYPE_TOKEN_SET, _BASE_TOKEN_ARTIFACT_ID, data=data, source=path
        )
        return result

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
        result = ThemePack(
            theme_id=str(data["theme_id"]),
            version=str(data["version"]),
            brand_id=str(data["brand_id"]),
            schema_version=int(data["schema_version"]),
            token_overrides={k: _coerce_value(k, v) for k, v in overrides.items()},
        )
        self._ensure_gov_loaded(
            _ARTIFACT_TYPE_THEME, str(data["theme_id"]), data=data, source=path
        )
        return result

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

        result = LayoutDefinition(
            layout_id=str(data["layout_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            regions=regions,
            constraints=constraints,
        )
        self._ensure_gov_loaded(
            _ARTIFACT_TYPE_LAYOUT, str(data["layout_id"]), data=data, source=path
        )
        return result

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

        result = SlidePrimitiveDefinition(
            primitive_id=str(data["primitive_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            layout_id=str(data["layout_id"]),
            slots=slots,
            constraints=constraints,
        )
        self._ensure_gov_loaded(
            _ARTIFACT_TYPE_PRIMITIVE, str(data["primitive_id"]), data=data, source=path
        )
        return result

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

        result = AssetDefinition(
            asset_id=str(data["asset_id"]),
            version=str(data["version"]),
            schema_version=int(data["schema_version"]),
            type=asset_type,
            source=str(data["source"]),
            metadata=dict(raw_metadata),
        )
        self._ensure_gov_loaded(
            _ARTIFACT_TYPE_ASSET, str(data["asset_id"]), data=data, source=path
        )
        return result

    def list_assets(self) -> list[str]:
        """Return a sorted list of registered asset IDs."""
        assets_dir = self._root / "assets"
        if not assets_dir.is_dir():
            return []
        return sorted(p.stem for p in assets_dir.glob("*.yaml"))

    # ------------------------------------------------------------------
    # Phase 10A — Governance read-only API
    # ------------------------------------------------------------------

    def get_artifact_governance(
        self,
        artifact_type: str,
        artifact_id: str,
        version: str,
    ) -> GovernedArtifactVersion | None:
        """Return governance metadata for the given artifact version, or ``None``.

        Loads the artifact YAML lazily if not yet cached.

        Args:
            artifact_type: Canonical type string (``"primitive"``, ``"layout"``,
                ``"theme"``, ``"asset"``, ``"token_set"``).
            artifact_id:   Stable artifact identifier.
            version:       Version string (e.g. ``"1.0.0"``).

        Returns:
            :class:`~.governance_models.GovernedArtifactVersion` or ``None``
            if the artifact cannot be found.
        """
        self._ensure_gov_loaded(artifact_type, artifact_id)
        return self._gov_versions.get((artifact_type, artifact_id, version))

    def get_artifact_family(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> GovernedArtifactFamily | None:
        """Return family metadata for the given artifact, or ``None``.

        Loads the artifact YAML lazily if not yet cached.  Even artifacts
        without an explicit ``family:`` block will have a family entry
        (with ``default_version=None``) once loaded.

        Args:
            artifact_type: Canonical type string.
            artifact_id:   Stable artifact identifier.

        Returns:
            :class:`~.governance_models.GovernedArtifactFamily` or ``None``
            if the artifact cannot be found.
        """
        self._ensure_gov_loaded(artifact_type, artifact_id)
        return self._gov_families.get((artifact_type, artifact_id))

    def list_artifact_versions(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> list[GovernedArtifactVersion]:
        """Return all known governance versions for *artifact_id*.

        In the current single-file-per-artifact design this list contains at
        most one entry.  The method is designed for future multi-version
        support where multiple YAML files may represent different versions of
        the same artifact.

        Args:
            artifact_type: Canonical type string.
            artifact_id:   Stable artifact identifier.

        Returns:
            List of :class:`~.governance_models.GovernedArtifactVersion`
            instances (may be empty if the artifact is not found).
        """
        self._ensure_gov_loaded(artifact_type, artifact_id)
        return [
            gov
            for (at, aid, _ver), gov in self._gov_versions.items()
            if at == artifact_type and aid == artifact_id
        ]

    def resolve_artifact_version(
        self,
        artifact_type: str,
        artifact_id: str,
        version: str | None = None,
    ) -> str | None:
        """Return the version string to use for *artifact_id*, or ``None``.

        Read-only lookup — does not enforce lifecycle status.  Draft and
        deprecated artifacts are returned without error at this stage;
        enforcement is Phase 10B.

        Case 1 — *version* is provided:
            If that version is recorded in the governance index, return it.
            If it is not known (artifact not found or version absent), return
            ``None``.

        Case 2 — *version* is ``None``:
            Return the ``default_version`` from the artifact family if one has
            been declared.  Return ``None`` when no default has been set.

        Args:
            artifact_type: Canonical type string (``"primitive"``,
                ``"layout"``, ``"theme"``, ``"asset"``, ``"token_set"``).
            artifact_id:   Stable artifact identifier.
            version:       Explicit version string, or ``None`` to request
                           the family default.

        Returns:
            A version string (e.g. ``"1.0.0"``) or ``None``.
        """
        self._ensure_gov_loaded(artifact_type, artifact_id)

        if version is not None:
            # Explicit version: return it only if it exists in the index.
            if (artifact_type, artifact_id, version) in self._gov_versions:
                return version
            return None

        # No explicit version: delegate to family default_version.
        family = self._gov_families.get((artifact_type, artifact_id))
        if family is not None:
            return family.default_version
        return None

    def enforce_artifact_lifecycle(
        self,
        artifact_type: str,
        artifact_id: str,
        version: str,
        *,
        allow_draft: bool = False,
        warnings: list[str] | None = None,
    ) -> None:
        """Enforce lifecycle policy for a resolved artifact version.

        - ``APPROVED`` — no action.
        - ``DRAFT``    — raises :class:`~.exceptions.GovernanceViolationError`
          when *allow_draft* is ``False``.
        - ``DEPRECATED`` — appends a human-readable warning to *warnings*
          (never raises).

        When *version* is not found in the governance index (e.g. the artifact
        YAML has no ``governance:`` block) the method is a no-op — enforcement
        is best-effort and requires explicit governance metadata.

        Args:
            artifact_type: Canonical artifact type (``"primitive"``, etc.).
            artifact_id:   Stable artifact identifier.
            version:       Artifact version string (e.g. ``"1.0.0"``).
            allow_draft:   When ``True``, DRAFT artifacts are permitted.
            warnings:      Mutable list to which deprecation warnings are
                           appended.  Pass ``None`` to silently discard them.

        Raises:
            GovernanceViolationError: If the artifact is DRAFT and
                *allow_draft* is ``False``.
        """
        self._ensure_gov_loaded(artifact_type, artifact_id)
        gov = self._gov_versions.get((artifact_type, artifact_id, version))
        if gov is None:
            return  # No governance metadata — enforcement is a no-op.

        if gov.lifecycle_status == LifecycleStatus.DRAFT and not allow_draft:
            raise GovernanceViolationError(
                f"{artifact_type.capitalize()} '{artifact_id}' version '{version}' "
                f"is in DRAFT status and cannot be used in production pipelines. "
                f"Set allow_draft_artifacts=True to permit draft artifacts."
            )

        if gov.lifecycle_status == LifecycleStatus.DEPRECATED:
            reason = (
                f" Reason: {gov.deprecation_reason}" if gov.deprecation_reason else ""
            )
            msg = (
                f"{artifact_type.capitalize()} '{artifact_id}' version '{version}' "
                f"is DEPRECATED and will be removed in a future release.{reason}"
            )
            if warnings is not None:
                warnings.append(msg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _artifact_yaml_path(self, artifact_type: str, artifact_id: str) -> Path | None:
        """Return the expected YAML path for *artifact_type* / *artifact_id*.

        Returns ``None`` for unknown artifact types.  The returned path is not
        guaranteed to exist — callers must check before opening.
        """
        subdir = _ARTIFACT_SUBDIR.get(artifact_type)
        if subdir is None:
            return None
        if artifact_type == _ARTIFACT_TYPE_TOKEN_SET:
            # There is exactly one base token file, regardless of artifact_id.
            return self._root / subdir / "base_tokens.yaml"
        return self._root / subdir / f"{artifact_id}.yaml"

    def _ensure_gov_loaded(
        self,
        artifact_type: str,
        artifact_id: str,
        *,
        data: dict[str, Any] | None = None,
        source: Path | None = None,
    ) -> None:
        """Populate governance indexes for *artifact_type* / *artifact_id*.

        When *data* and *source* are supplied (i.e. called from an existing
        getter that has already loaded the YAML) they are used directly,
        avoiding a second disk read.  When called without them (i.e. from a
        governance method that needs to load on-demand), the YAML is read
        from disk using :meth:`_artifact_yaml_path`.

        Calling this method more than once for the same key is a no-op.
        """
        load_key = (artifact_type, artifact_id)
        if load_key in self._gov_loaded:
            return

        if data is None or source is None:
            path = self._artifact_yaml_path(artifact_type, artifact_id)
            if path is None or not path.exists():
                return
            try:
                data = self._load_yaml(path)
            except DesignSystemSchemaError:
                return
            source = path

        version = str(data.get("version", "0.0.0"))
        gov, family = _parse_governance_block(
            data, artifact_type, artifact_id, version, source
        )
        self._gov_versions[(artifact_type, artifact_id, version)] = gov
        self._gov_families[(artifact_type, artifact_id)] = family
        self._gov_loaded.add(load_key)

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
