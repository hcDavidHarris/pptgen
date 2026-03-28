"""Asset resolver — Phase 9 Stage 4.

Walks a deck definition dict, detects ``{"asset_id": "<id>"}`` reference dicts,
resolves each against the registry, and returns a new dict with every reference
replaced by its resolved inline metadata.

Resolution is deterministic and fail-fast: an unknown ``asset_id`` raises
immediately.  Silent fallback is prohibited.
"""

from __future__ import annotations

from typing import Any

from .asset_models import ASSET_REF_KEY, ResolvedAsset
from .dependency_models import ResolvedArtifactDependency, record_dependency
from .exceptions import UnknownAssetError
from .registry import DesignSystemRegistry


class AssetResolver:
    """Resolves ``asset_id`` references embedded in deck content.

    Usage::

        registry = DesignSystemRegistry(settings.design_system_root)
        resolver = AssetResolver()
        new_deck, resolved = resolver.resolve_references(deck_definition, registry)
    """

    def resolve_references(
        self,
        deck_definition: dict[str, Any],
        registry: DesignSystemRegistry,
        *,
        allow_draft: bool = False,
        governance_warnings: list[str] | None = None,
        dependency_chain: list[ResolvedArtifactDependency] | None = None,
    ) -> tuple[dict[str, Any], list[ResolvedAsset]]:
        """Walk *deck_definition* and replace every asset reference in-place.

        An asset reference is any dict value that contains the key
        ``"asset_id"`` (see :data:`~.asset_models.ASSET_REF_KEY`).  It is
        replaced with :meth:`~.asset_models.ResolvedAsset.as_inline` — a dict
        that keeps ``asset_id`` for traceability and adds ``resolved_source``,
        ``type``, and ``version``.

        Args:
            deck_definition: Plain dict representation of the deck at the
                             current pipeline stage.
            registry:        Loaded :class:`~.registry.DesignSystemRegistry`.

        Returns:
            A ``(new_deck_definition, resolved_assets)`` tuple.
            *new_deck_definition* is a new dict with all references resolved.
            *resolved_assets* is the de-duplicated list of
            :class:`~.asset_models.ResolvedAsset` instances encountered
            (order of first occurrence).

        Raises:
            UnknownAssetError:        An ``asset_id`` value is not in the
                                      registry.
            InvalidAssetDefinitionError: The matching asset YAML is malformed.
            InvalidAssetTypeError:    The matching asset declares an invalid
                                      type.
        """
        resolved_index: dict[str, ResolvedAsset] = {}
        new_deck = _walk(
            deck_definition, registry, resolved_index,
            allow_draft=allow_draft,
            governance_warnings=governance_warnings,
            dependency_chain=dependency_chain,
        )
        # Preserve first-occurrence order.
        return new_deck, list(resolved_index.values())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _walk(
    obj: Any,
    registry: DesignSystemRegistry,
    resolved_index: dict[str, ResolvedAsset],
    *,
    allow_draft: bool = False,
    governance_warnings: list[str] | None = None,
    dependency_chain: list[ResolvedArtifactDependency] | None = None,
) -> Any:
    """Recursively walk *obj*, resolving asset references."""
    if isinstance(obj, dict):
        if ASSET_REF_KEY in obj:
            return _resolve_ref(
                obj, registry, resolved_index,
                allow_draft=allow_draft,
                governance_warnings=governance_warnings,
                dependency_chain=dependency_chain,
            )
        return {
            k: _walk(
                v, registry, resolved_index,
                allow_draft=allow_draft,
                governance_warnings=governance_warnings,
                dependency_chain=dependency_chain,
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [
            _walk(
                item, registry, resolved_index,
                allow_draft=allow_draft,
                governance_warnings=governance_warnings,
                dependency_chain=dependency_chain,
            )
            for item in obj
        ]
    return obj


def _resolve_ref(
    ref: dict[str, Any],
    registry: DesignSystemRegistry,
    resolved_index: dict[str, ResolvedAsset],
    *,
    allow_draft: bool = False,
    governance_warnings: list[str] | None = None,
    dependency_chain: list[ResolvedArtifactDependency] | None = None,
) -> dict[str, Any]:
    """Resolve a single ``{asset_id: ...}`` reference dict.

    Caches resolved assets in *resolved_index* so each asset is only looked
    up once per resolution pass (deterministic, no repeat I/O).  Dependency
    capture is also guarded by this cache — each asset is recorded at most
    once per run.

    Raises:
        UnknownAssetError: Asset ID is not registered.
        GovernanceViolationError: When the asset is DRAFT and allow_draft is False.
    """
    asset_id = ref[ASSET_REF_KEY]
    if not isinstance(asset_id, str) or not asset_id:
        raise UnknownAssetError(
            f"Invalid asset reference: 'asset_id' must be a non-empty string, "
            f"got {type(asset_id).__name__!r}."
        )

    if asset_id not in resolved_index:
        # Raises UnknownAssetError / InvalidAssetDefinitionError / InvalidAssetTypeError.
        definition = registry.get_asset(asset_id)
        registry.enforce_artifact_lifecycle(
            "asset", asset_id, definition.version,
            allow_draft=allow_draft,
            warnings=governance_warnings,
        )
        if dependency_chain is not None:
            gov = registry.get_artifact_governance(
                "asset", asset_id, definition.version
            )
            record_dependency(
                dependency_chain,
                "asset", asset_id, definition.version,
                gov.lifecycle_status.value if gov else None,
                "asset",
            )
        resolved_index[asset_id] = ResolvedAsset(
            asset_id=definition.asset_id,
            version=definition.version,
            type=definition.type,
            resolved_source=definition.source,
        )

    return resolved_index[asset_id].as_inline()
