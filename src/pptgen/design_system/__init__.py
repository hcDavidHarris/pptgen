"""Design system — Phase 9 Stage 1 / Stage 2 / Stage 3 / Stage 4.

Public API::

    from pptgen.design_system import (
        # Stage 1 — tokens
        DesignSystemRegistry,
        TokenResolver,
        BaseTokenSet,
        BrandPack,
        ThemePack,
        ResolvedStyleMap,
        # Stage 2 — layouts
        LayoutResolver,
        LayoutDefinition,
        LayoutConstraints,
        RegionDefinition,
        ResolvedLayout,
        # Stage 3 — primitives
        PrimitiveResolver,
        SlidePrimitiveDefinition,
        PrimitiveConstraints,
        SlotDefinition,
        ResolvedSlidePrimitive,
        # Exceptions
        DesignSystemError,
        UnknownTokenError,
        UnknownThemeError,
        UnknownBrandError,
        InvalidTokenOverrideError,
        DesignSystemSchemaError,
        UnknownLayoutError,
        MissingRequiredSlotError,
        UnknownSlotError,
        InvalidLayoutDefinitionError,
        UnknownPrimitiveError,
        MissingRequiredContentError,
        UnknownContentFieldError,
        InvalidContentTypeError,
        InvalidPrimitiveDefinitionError,
    )
"""

from .asset_models import AssetDefinition, ResolvedAsset
from .governance_models import GovernedArtifactFamily, GovernedArtifactVersion, LifecycleStatus
from .asset_resolver import AssetResolver
from .exceptions import (
    DesignSystemError,
    DesignSystemSchemaError,
    InvalidAssetDefinitionError,
    InvalidAssetTypeError,
    InvalidContentTypeError,
    InvalidLayoutDefinitionError,
    InvalidPrimitiveDefinitionError,
    InvalidTokenOverrideError,
    MissingRequiredContentError,
    MissingRequiredSlotError,
    UnknownAssetError,
    UnknownBrandError,
    UnknownContentFieldError,
    UnknownLayoutError,
    UnknownPrimitiveError,
    UnknownSlotError,
    UnknownThemeError,
    UnknownTokenError,
)
from .layout_models import LayoutConstraints, LayoutDefinition, RegionDefinition, ResolvedLayout
from .layout_resolver import LayoutResolver
from .models import BaseTokenSet, BrandPack, ResolvedStyleMap, ThemePack
from .primitive_models import (
    PrimitiveConstraints,
    ResolvedSlidePrimitive,
    SlidePrimitiveDefinition,
    SlotDefinition,
)
from .primitive_resolver import PrimitiveResolver
from .registry import DesignSystemRegistry
from .token_resolver import TokenResolver

__all__ = [
    # Phase 10A — governance models
    "GovernedArtifactFamily",
    "GovernedArtifactVersion",
    "LifecycleStatus",
    # Stage 1 — tokens
    "BaseTokenSet",
    "BrandPack",
    "DesignSystemError",
    "DesignSystemRegistry",
    "DesignSystemSchemaError",
    "InvalidTokenOverrideError",
    "ResolvedStyleMap",
    "ThemePack",
    "TokenResolver",
    "UnknownBrandError",
    "UnknownThemeError",
    "UnknownTokenError",
    # Stage 2 — layouts
    "InvalidLayoutDefinitionError",
    "LayoutConstraints",
    "LayoutDefinition",
    "LayoutResolver",
    "MissingRequiredSlotError",
    "RegionDefinition",
    "ResolvedLayout",
    "UnknownLayoutError",
    "UnknownSlotError",
    # Stage 4 — assets
    "AssetDefinition",
    "AssetResolver",
    "InvalidAssetDefinitionError",
    "InvalidAssetTypeError",
    "ResolvedAsset",
    "UnknownAssetError",
    # Stage 3 — primitives
    "InvalidContentTypeError",
    "InvalidPrimitiveDefinitionError",
    "MissingRequiredContentError",
    "PrimitiveConstraints",
    "PrimitiveResolver",
    "ResolvedSlidePrimitive",
    "SlidePrimitiveDefinition",
    "SlotDefinition",
    "UnknownContentFieldError",
    "UnknownPrimitiveError",
]
