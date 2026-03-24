"""Custom exceptions for the pptgen platform.

Every exception carries a ``category`` class attribute from :class:`ErrorCategory`.
This allows operator tooling, retry policies, and structured logging to classify
failures without inspecting exception types directly.
"""

from __future__ import annotations

from enum import Enum


class ErrorCategory(str, Enum):
    """Normalized failure categories for operator tooling and retry policy."""

    VALIDATION = "validation"       # Bad input — client-fixable
    CONNECTOR = "connector"         # Source file parsing failure
    AI_PROVIDER = "ai_provider"     # LLM call failure
    PLANNING = "planning"           # Slide planner failure
    RENDERING = "rendering"         # python-pptx / template failure
    CONFIGURATION = "configuration" # Missing or invalid config / registry entry
    WORKSPACE = "workspace"         # Workspace or I/O failure
    TIMEOUT = "timeout"             # Stage exceeded its time limit
    SYSTEM = "system"               # Unexpected / internal error


class PptgenError(Exception):
    """Base exception for all pptgen errors.

    Subclasses set ``category`` as a class attribute so callers can inspect
    failure type without catching each subclass individually::

        try:
            ...
        except PptgenError as exc:
            if exc.category == ErrorCategory.CONFIGURATION:
                ...
    """

    category: ErrorCategory = ErrorCategory.SYSTEM


# ---------------------------------------------------------------------------
# Existing error types — unchanged behaviour; category added
# ---------------------------------------------------------------------------

class YAMLLoadError(PptgenError):
    """Raised when a YAML file cannot be read or parsed by PyYAML."""

    category = ErrorCategory.VALIDATION


class ParseError(PptgenError):
    """Raised when YAML content does not conform to the DeckFile model structure."""

    category = ErrorCategory.VALIDATION


class RegistryError(PptgenError):
    """Raised when the template registry cannot be loaded or is malformed."""

    category = ErrorCategory.CONFIGURATION


class TemplateLoadError(PptgenError):
    """Raised when a template .pptx file cannot be opened."""

    category = ErrorCategory.CONFIGURATION


class TemplateCompatibilityError(PptgenError):
    """Raised when a template is missing a required layout or placeholder."""

    category = ErrorCategory.CONFIGURATION


# ---------------------------------------------------------------------------
# New error types introduced in Stage 6A
# ---------------------------------------------------------------------------

class InputSizeError(PptgenError):
    """Raised when the input text exceeds the configured ``max_input_bytes`` limit."""

    category = ErrorCategory.VALIDATION


class WorkspaceError(PptgenError):
    """Raised when a runtime workspace cannot be created, accessed, or cleaned up."""

    category = ErrorCategory.WORKSPACE


class ConfigurationError(PptgenError):
    """Raised when a required configuration value is missing or invalid at startup."""

    category = ErrorCategory.CONFIGURATION


class PptgenTimeoutError(PptgenError):
    """Raised when a pipeline stage exceeds its configured time limit.

    Named ``PptgenTimeoutError`` to avoid shadowing the built-in
    ``TimeoutError``.  Import as ``from pptgen.errors import PptgenTimeoutError``.
    """

    category = ErrorCategory.TIMEOUT
