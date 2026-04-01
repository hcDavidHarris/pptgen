"""Versioned template registry — Phase 8 Stage 1.

Provides in-memory lookup for :class:`~pptgen.templates.models.Template` and
:class:`~pptgen.templates.models.TemplateVersion` objects loaded from the
versioned manifest (``templates/registry/templates.yaml``).
"""
from __future__ import annotations

from pathlib import Path

from .manifest_loader import load_template_manifest
from .models import Template, TemplateVersion


def _parse_semver(v: str) -> tuple[int, ...]:
    """Parse a semantic version string into a comparable tuple."""
    try:
        return tuple(int(x) for x in v.split("."))
    except (ValueError, AttributeError):
        return (0,)


class VersionedTemplateRegistry:
    """In-memory registry of versioned templates loaded from a manifest file.

    Usage::

        reg = VersionedTemplateRegistry.from_manifest(Path("templates/registry/templates.yaml"))
        tmpl = reg.get_template("executive_brief_v1")
        ver  = reg.get_template_version("executive_brief_v1", "1.0.0")
    """

    def __init__(self, templates: list[Template]) -> None:
        self._templates: dict[str, Template] = {
            t.template_id: t for t in templates
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_manifest(cls, path: Path) -> VersionedTemplateRegistry:
        """Load the manifest at *path* and return a registry instance."""
        return cls(load_template_manifest(path))

    @classmethod
    def default_manifest_path(cls) -> Path:
        """Return the canonical manifest path relative to this package."""
        # src/pptgen/templates/registry.py → up 4 levels → repo root
        return (
            Path(__file__).parent.parent.parent.parent
            / "templates"
            / "registry"
            / "templates.yaml"
        )

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def list_templates(self) -> list[Template]:
        """Return all registered templates."""
        return list(self._templates.values())

    def get_template(self, template_id: str) -> Template | None:
        """Return the template for *template_id*, or ``None``."""
        return self._templates.get(template_id)

    def get_template_versions(self, template_id: str) -> list[TemplateVersion]:
        """Return versions for *template_id* sorted by ascending semantic version."""
        t = self._templates.get(template_id)
        if t is None:
            return []
        return sorted(t.versions, key=lambda v: _parse_semver(v.version))

    def get_template_version(
        self, template_id: str, version: str
    ) -> TemplateVersion | None:
        """Return the exact version match, or ``None``."""
        for v in self.get_template_versions(template_id):
            if v.version == version:
                return v
        return None

    def get_approved_templates(self) -> list[Template]:
        """Return only templates with lifecycle_status == 'approved'."""
        return [
            t for t in self._templates.values()
            if t.lifecycle_status == "approved"
        ]
