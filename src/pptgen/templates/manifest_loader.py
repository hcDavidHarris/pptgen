"""Template manifest loader — Phase 8 Stage 1.

Loads templates/registry/templates.yaml (versioned manifest format), validates
the schema, and returns a list of :class:`~pptgen.templates.models.Template`
instances with computed revision hashes.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import yaml

from ..errors import RegistryError
from .models import Template, TemplateVersion


# ---------------------------------------------------------------------------
# Hash + ID helpers
# ---------------------------------------------------------------------------

def compute_template_revision_hash(
    template_id: str,
    version: str,
    entry: dict,
) -> str:
    """Return a 16-char SHA-256 digest of the version manifest entry.

    The hash covers all content-affecting fields so that any change to the
    template definition produces a different hash.  This enables replay safety
    verification: a run can confirm its pinned hash still matches the current
    manifest entry.
    """
    payload = json.dumps(
        {
            "template_id": template_id,
            "version": version,
            "template_path": entry.get("template_path"),
            "playbook_path": entry.get("playbook_path"),
            "input_contract_version": entry.get("input_contract_version"),
            "ai_mode": entry.get("ai_mode", "optional"),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _make_version_id(template_id: str, version: str) -> str:
    """Return a deterministic UUID5 for (template_id, version)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"pptgen/{template_id}/{version}"))


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def validate_manifest_schema(data: Any) -> None:
    """Raise :exc:`RegistryError` if *data* is not a valid manifest structure."""
    if not isinstance(data, dict):
        raise RegistryError("Template manifest must be a YAML mapping")
    if "templates" not in data:
        raise RegistryError("Template manifest must have a top-level 'templates' key")
    templates = data["templates"]
    if not isinstance(templates, dict):
        raise RegistryError(
            "'templates' must be a mapping of template_id → entry (not a list)"
        )
    for tid, entry in templates.items():
        if not isinstance(entry, dict):
            raise RegistryError(
                f"Template entry '{tid}' must be a YAML mapping"
            )
        if "versions" not in entry:
            raise RegistryError(
                f"Template entry '{tid}' must have a 'versions' list"
            )
        if not isinstance(entry["versions"], list) or len(entry["versions"]) == 0:
            raise RegistryError(
                f"Template '{tid}' must have at least one version"
            )
        for i, v in enumerate(entry["versions"]):
            if not isinstance(v, dict) or "version" not in v:
                raise RegistryError(
                    f"Version entry [{i}] in template '{tid}' must have a 'version' field"
                )


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------

def load_template_manifest(path: Path) -> list[Template]:
    """Load *path* and return a list of :class:`Template` instances.

    Raises:
        RegistryError: on file I/O errors, YAML parse errors, or schema violations.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RegistryError(
            f"Cannot read template manifest '{path}': {exc}"
        ) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RegistryError(
            f"YAML parse error in template manifest '{path}': {exc}"
        ) from exc

    validate_manifest_schema(data)

    templates: list[Template] = []
    for template_id, entry in data["templates"].items():
        versions: list[TemplateVersion] = []
        for v_entry in entry["versions"]:
            ver = str(v_entry["version"])
            rev_hash = compute_template_revision_hash(template_id, ver, v_entry)
            versions.append(
                TemplateVersion(
                    version_id=_make_version_id(template_id, ver),
                    template_id=template_id,
                    version=ver,
                    template_revision_hash=rev_hash,
                    template_path=v_entry.get("template_path"),
                    playbook_path=v_entry.get("playbook_path"),
                    input_contract_version=v_entry.get("input_contract_version"),
                    ai_mode=v_entry.get("ai_mode", "optional"),
                )
            )

        templates.append(
            Template(
                template_id=template_id,
                template_key=template_id,
                name=entry.get("name", template_id),
                description=entry.get("description"),
                owner=entry.get("owner"),
                lifecycle_status=entry.get("lifecycle_status", "draft"),
                versions=versions,
            )
        )

    return templates
