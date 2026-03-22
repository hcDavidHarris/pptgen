# pptgen Authority Map

Version: 1.0
Owner: Analytics / DevOps Platform Team

This document declares the single source of truth for every major subsystem
in the pptgen platform. When two locations define the same data, the
authority listed here wins. All other locations are derived views and should
be updated to match, not the other way around.

---

## Source-of-Truth Table

| Subsystem | Authoritative Source | Derived / Mirror Locations | Notes |
|---|---|---|---|
| Slide type definitions (fields, required/optional) | `src/pptgen/models/slides.py` — Pydantic model classes | `docs/authoring/slide_type_reference.md`, `schemas/deck.schema.json`, `docs/architecture/authoring_contract.md` | Pydantic enforces the contract at parse time; other locations are documentation |
| Slide type metadata (max_items, layout name, placeholders) | `src/pptgen/slide_registry.py` — `SLIDE_TYPE_REGISTRY` | `src/pptgen/render/deck_renderer.py` (`SLIDE_TYPE_TO_LAYOUT`, `_SLIDE_TYPE_PH_NAMES`), `templates/registry.yaml` `supported_slide_types`, `docs/authoring/slide_type_reference.md` | `SLIDE_TYPE_TO_LAYOUT` and `_SLIDE_TYPE_PH_NAMES` in deck_renderer.py mirror this data and must be kept in sync — a known drift risk |
| Placeholder idx → name mapping | `src/pptgen/render/deck_renderer.py` — `_SLIDE_TYPE_PH_NAMES` | `docs/template_placeholder_inventory.md` | idx values come from the template .pptx file itself and cannot be centralised without reading the file at import time |
| Validation rules (semantic) | `src/pptgen/validators/deck_validator.py` | `docs/architecture/authoring_contract.md`, `schemas/deck.schema.json` | JSON schema is a portable reference artifact; Pydantic + deck_validator.py is the runtime enforcement authority |
| Template registry (which templates exist, their paths and status) | `templates/registry.yaml` | `pptgen list-templates` CLI output | CLI reads directly from registry.yaml at runtime |
| Slide renderer dispatch | `src/pptgen/render/slide_renderers.py` — `SLIDE_RENDERERS` dict | None | If a type is missing from SLIDE_RENDERERS, render_deck() raises KeyError at runtime |
| Example decks (canonical content patterns) | `examples/` directory YAML files | `examples/catalog.yaml`, `docs/examples/example_index.md` | All example YAML must pass `pptgen validate` before commit |
| AI routing logic | `docs/ai-playbooks/routing_table.yaml` | `docs/architecture/system_map.md` (workflow diagram) | Routing table is consumed by AI skills; it is a policy document, not runtime code |
| CLI command structure | `src/pptgen/cli/__init__.py` — Typer app registration | `docs/guides/repository_guide.md` | Sub-apps registered via `app.add_typer()`; the module listing in `__init__.py` is authoritative |
| Deck YAML schema (portable/external) | `schemas/deck.schema.json` | Generated from `src/pptgen/models/` — must be kept in sync manually | NOT integrated into the runtime validator; used by IDEs and CI external tooling |
| Workspace directory structure | `docs/workspace/workspace_model.md` | `src/pptgen/cli/workspace_init.py` (mkdir list) | workspace_init.py creates directories; workspace_model.md defines the contract |
| Template placeholder naming contract | `docs/template_placeholder_inventory.md` | Template .pptx layout shape names | The .pptx file is the ground truth at render time; the doc is a human-readable specification |

---

## Drift Risks

The following pairs are **not** automatically kept in sync. A change to the
authority source requires a manual update to the mirror location.

### Risk 1: `slide_registry.py` ↔ `deck_renderer.py`

`SLIDE_TYPE_TO_LAYOUT` and `_SLIDE_TYPE_PH_NAMES` in `deck_renderer.py`
duplicate data that is also in `SLIDE_TYPE_REGISTRY`. These were not
refactored to import from the registry because `_SLIDE_TYPE_PH_NAMES`
contains `placeholder_format.idx` values that are determined by the .pptx
template file, not by the registry.

**Rule:** When adding a slide type, update both `slide_registry.py` AND
`deck_renderer.py`. The registry check in the index.yaml `add_slide_type`
task lists both files explicitly.

### Risk 2: `models/slides.py` ↔ `schemas/deck.schema.json`

The JSON schema is maintained manually. It does not auto-generate from
Pydantic models. Any field added to a Pydantic model must also be added to
the corresponding JSON Schema definition.

**Rule:** After modifying `models/slides.py`, update `schemas/deck.schema.json`
before committing.

### Risk 3: `slide_registry.py` ↔ `templates/registry.yaml` `supported_slide_types`

The registry.yaml `supported_slide_types` list per template is declared
manually and is not validated against `SLIDE_TYPE_REGISTRY` at runtime.

**Rule:** When a new slide type is added and its layout is added to a
template .pptx, update the template's `supported_slide_types` in
`templates/registry.yaml`.

---

## Invariants

These properties must hold at all times. CI or the template contract
validator will detect violations.

1. Every key in `SLIDE_RENDERERS` must have a corresponding entry in
   `SLIDE_TYPE_REGISTRY`.
2. Every key in `SLIDE_TYPE_TO_LAYOUT` must have a corresponding entry in
   `SLIDE_RENDERERS`.
3. All YAML files in `examples/` must pass `pptgen validate` with no errors.
4. All placeholder names in templates must be `UPPERCASE_SNAKE_CASE`.
5. `extra='forbid'` must not be relaxed on any Pydantic model.
6. Template IDs in `templates/registry.yaml` must be unique.

---

## Can a new AI coding agent safely modify this repository?

**MOSTLY YES**, with the following conditions:

- The agent **must** read `docs/ai-navigation/index.yaml` first to find the
  correct files for any given task type.
- The agent **must** run `pptgen validate` on any example YAML it creates or
  modifies before committing.
- The agent **must** update all mirror locations listed in the Drift Risks
  section when modifying an authority source.
- The agent **must not** relax `extra='forbid'` on any model.
- The agent **must not** modify `pyproject.toml` entry points.
- The agent **should** run `pytest` before committing any Python changes.

The primary failure mode for a new agent is modifying one location in a
drift-risk pair without updating the other (e.g., adding a slide type to
`slide_registry.py` but forgetting `deck_renderer.py` or `SLIDE_RENDERERS`).
The `add_slide_type` task in `docs/ai-navigation/index.yaml` lists all
required files in the correct order to prevent this.
