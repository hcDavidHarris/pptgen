"""Template registry module — Phase 8 Stage 1."""

from .models import Template, TemplateVersion
from .registry import VersionedTemplateRegistry
from .resolution import (
    resolve_template_default_version,
    resolve_template_for_replay,
    resolve_template_for_run,
)
from .store import clear_registry, get_registry, load_registry

__all__ = [
    "Template",
    "TemplateVersion",
    "VersionedTemplateRegistry",
    "resolve_template_for_run",
    "resolve_template_for_replay",
    "resolve_template_default_version",
    "load_registry",
    "get_registry",
    "clear_registry",
]
