"""Template registry store — cached module-level singleton.

The server lifespan calls :func:`load_registry` once at startup.  All other
code obtains the registry via :func:`get_registry` without re-reading the
manifest file on every call.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .registry import VersionedTemplateRegistry

_registry: Optional[VersionedTemplateRegistry] = None


def load_registry(manifest_path: Optional[Path] = None) -> VersionedTemplateRegistry:
    """Load (or reload) the registry from *manifest_path*.

    If *manifest_path* is ``None`` the canonical default path is used
    (``templates/registry/templates.yaml`` relative to the repo root).
    """
    global _registry
    path = manifest_path or VersionedTemplateRegistry.default_manifest_path()
    _registry = VersionedTemplateRegistry.from_manifest(path)
    return _registry


def get_registry() -> Optional[VersionedTemplateRegistry]:
    """Return the cached registry, or ``None`` if not yet loaded."""
    return _registry


def clear_registry() -> None:
    """Clear the cached registry (primarily for use in tests)."""
    global _registry
    _registry = None
