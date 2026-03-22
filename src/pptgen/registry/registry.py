"""Template registry loader.

The registry is a YAML file (``templates/registry.yaml``) that lists all
approved pptgen templates.  Its structure is:

    templates:
      - template_id: ops_review_v1
        version: "1.0"
        owner: Analytics Services
        backup_owner: DevOps Platform Team
        status: approved
        path: templates/ops_review_v1/template.pptx
        supported_slide_types:
          - title
          - bullets
          - metric_summary

The ``path`` field records where the physical ``.pptx`` file lives.  Phase 1
only reads this metadata; the renderer (Phase 2) will actually open the file.

TemplateRegistry is intentionally read-only — no write operations are needed
in Phase 1.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from ..errors import RegistryError


class TemplateEntry(BaseModel):
    """Metadata for a single registered template.

    ``extra='ignore'`` is used deliberately here: the registry format may
    grow additional fields (e.g. ``max_metrics``, ``source``) and we do not
    want the registry loader to break when new fields are added.
    """

    model_config = ConfigDict(extra="ignore")

    template_id: str
    version: str
    owner: str
    status: str
    path: str
    supported_slide_types: list[str]
    backup_owner: str | None = None
    max_metrics: int = 4


class TemplateRegistry:
    """In-memory view of the template registry file.

    Usage::

        registry = TemplateRegistry.from_file(Path("templates/registry.yaml"))
        entry = registry.get("ops_review_v1")
        if entry is None:
            ...
    """

    def __init__(self, entries: list[TemplateEntry]) -> None:
        self._entries: dict[str, TemplateEntry] = {
            e.template_id: e for e in entries
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: Path) -> TemplateRegistry:
        """Load and parse *path* into a TemplateRegistry.

        Raises:
            RegistryError: if the file cannot be read, is not valid YAML,
                           or is missing the required ``templates`` key.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RegistryError(f"Cannot read registry file '{path}': {exc}") from exc

        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise RegistryError(
                f"YAML parse error in registry file '{path}': {exc}"
            ) from exc

        if not isinstance(data, dict) or "templates" not in data:
            raise RegistryError(
                f"Registry file '{path}' must contain a top-level 'templates' list"
            )

        entries: list[TemplateEntry] = []
        for i, raw in enumerate(data["templates"]):
            try:
                entries.append(TemplateEntry.model_validate(raw))
            except ValidationError as exc:
                raise RegistryError(
                    f"Invalid entry at templates[{i}] in '{path}': {exc}"
                ) from exc

        return cls(entries)

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def get(self, template_id: str) -> TemplateEntry | None:
        """Return the entry for *template_id*, or ``None`` if not found."""
        return self._entries.get(template_id)

    def exists(self, template_id: str) -> bool:
        """Return ``True`` if *template_id* is present in the registry."""
        return template_id in self._entries

    def all(self) -> list[TemplateEntry]:
        """Return all registered template entries."""
        return list(self._entries.values())
