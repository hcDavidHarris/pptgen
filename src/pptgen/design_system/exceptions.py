"""Design system exceptions — Phase 9 Stage 1 / Stage 2."""

from __future__ import annotations

from ..errors import ErrorCategory, PptgenError


class DesignSystemError(PptgenError):
    """Base exception for all design system failures."""

    category = ErrorCategory.DESIGN_SYSTEM


class UnknownTokenError(DesignSystemError):
    """A template or config file references a token key not in the base token set.

    This triggers a run failure before rendering begins — silent fallback is
    prohibited by the Phase 9 specification.
    """


class UnknownThemeError(DesignSystemError):
    """A run or template references a theme that does not exist in the registry."""


class UnknownBrandError(DesignSystemError):
    """A theme references a brand that does not exist in the registry."""


class InvalidTokenOverrideError(DesignSystemError):
    """A brand or theme attempts to override a token not defined in the base set.

    This is a configuration error in the brand/theme YAML, not in the template.
    """


class DesignSystemSchemaError(DesignSystemError):
    """A design system YAML file does not match the expected schema."""


# ---------------------------------------------------------------------------
# Stage 2 — Layout primitive exceptions
# ---------------------------------------------------------------------------


class UnknownLayoutError(DesignSystemError):
    """A template references a layout that does not exist in the registry."""


class MissingRequiredSlotError(DesignSystemError):
    """A template omits a slot that a layout region marked as required."""


class UnknownSlotError(DesignSystemError):
    """A template declares a slot that does not match any region in the layout.

    Raised only when the layout's ``allow_extra_slots`` constraint is ``False``.
    """


class InvalidLayoutDefinitionError(DesignSystemError):
    """A layout YAML file is structurally invalid or fails schema validation."""


# ---------------------------------------------------------------------------
# Stage 3 — Slide component primitive exceptions
# ---------------------------------------------------------------------------


class UnknownPrimitiveError(DesignSystemError):
    """A template references a primitive that does not exist in the registry."""


class MissingRequiredContentError(DesignSystemError):
    """A template omits a content field that a primitive slot marked as required."""


class UnknownContentFieldError(DesignSystemError):
    """A template declares a content field not defined in the primitive's slots.

    Raised only when the primitive's ``allow_extra_content`` constraint is ``False``.
    """


class InvalidContentTypeError(DesignSystemError):
    """A template content field value does not match the declared ``content_type``."""


class InvalidPrimitiveDefinitionError(DesignSystemError):
    """A primitive YAML file is structurally invalid or fails schema validation."""


# ---------------------------------------------------------------------------
# Stage 4 — Asset system exceptions
# ---------------------------------------------------------------------------


class UnknownAssetError(DesignSystemError):
    """Deck content references an asset ID that does not exist in the registry."""


class InvalidAssetTypeError(DesignSystemError):
    """An asset definition declares an unsupported ``type`` value."""


class InvalidAssetDefinitionError(DesignSystemError):
    """An asset YAML file is structurally invalid or fails schema validation."""
