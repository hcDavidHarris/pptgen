# Repository Guide

Version: 1.0
Owner: Analytics / DevOps Platform Team

> **Note:** This guide covers the YAML authoring and template/schema areas of the repo.
> For the expanded platform (pipeline, API, connectors, Web UI), see
> [docs/development/repository_guide.md](../../docs/development/repository_guide.md).

A practical guide to navigating the pptgen repository. Where things live, what to touch when, and where not to go unless you know what you're doing.

---

## Top-Level Structure

```
pptgen/
|
+-- src/pptgen/           Python engine source code
+-- templates/            PowerPoint template files and registry
+-- examples/             Reference YAML deck patterns
+-- schemas/              JSON schema and deck pattern definitions
+-- skills/               Claude AI skill definitions
+-- docs/                 All documentation
+-- tests/                Test suite
+-- scripts/              Build and utility scripts
```

---

## Engine (`src/pptgen/`)

```
src/pptgen/
|
+-- cli/                  CLI entry points (Typer commands)
|   +-- __init__.py       Main app; build, validate, list-templates commands
|   +-- deck_scaffold.py  pptgen deck scaffold
|   +-- template_inspect.py  pptgen template inspect
|   +-- example_commands.py  pptgen example list / show / copy
|   +-- workspace_init.py    pptgen workspace init
|   +-- validation_explain.py  Error/warning explanation catalogue
|
+-- models/               Pydantic data models
|   +-- deck.py           DeckFile, DeckMetadata
|   +-- slides.py         All slide type models + SlideUnion
|
+-- loaders/
|   +-- yaml_loader.py    load_deck(), parse_deck(), load_yaml_file()
|
+-- validators/
|   +-- deck_validator.py validate_deck(), ValidationResult
|
+-- registry/
|   +-- registry.py       TemplateRegistry, TemplateEntry
|
+-- render/
|   +-- deck_renderer.py        render_deck(), SLIDE_TYPE_TO_LAYOUT, placeholder renaming
|   +-- slide_renderers.py      SLIDE_RENDERERS dict, per-type render_* functions
|   +-- placeholder_mapper.py   find_placeholder(), set_text(), set_bullets()
|   +-- template_inspector.py   inspect_template() → layout name map
|   +-- template_loader.py      load_template() → python-pptx Presentation
|
+-- slide_registry.py     SLIDE_TYPE_REGISTRY — slide type metadata
+-- template_contract_validator.py  validate_template_contract()
+-- errors/__init__.py    Custom exception hierarchy
```

### When to modify what

| Task | Files to change |
|---|---|
| Add a new slide type | `models/slides.py`, `render/slide_renderers.py`, `render/deck_renderer.py`, `slide_registry.py`, template .pptx, `templates/registry.yaml` |
| Add a new CLI command | `cli/<new_module>.py`, register in `cli/__init__.py` |
| Change validation rules | `validators/deck_validator.py` |
| Change max_items limits | `slide_registry.py` |
| Change placeholder names | `render/deck_renderer.py` (`_SLIDE_TYPE_PH_NAMES`), template .pptx |

---

## Templates (`templates/`)

```
templates/
|
+-- registry.yaml                   Template registry (the authoritative list)
+-- ops_review_v1/
|   +-- template.pptx               Standard ops review template
+-- executive_brief_v1/
|   +-- template.pptx               Executive brief template
+-- architecture_overview_v1/
|   +-- template.pptx               Architecture overview template
+-- HC_Powerpoint_Template_with_pptgen_placeholders.potx  Source branded template
```

### When to modify what

| Task | Files to change |
|---|---|
| Register a new template | `templates/registry.yaml` — add new entry |
| Update a template file | Replace the .pptx in its subdirectory |
| Check what templates exist | `pptgen list-templates` |
| Inspect a template's contract | `pptgen template inspect --template <id>` |
| Verify template against contract | `template_contract_validator.py` |

**Important:** Template IDs in `registry.yaml` must be unique. Keep separate IDs even when backed by the same .pptx file, to allow future divergence.

---

## Examples (`examples/`)

```
examples/
|
+-- eos/                   EOS leadership artifacts
+-- engineering_delivery/  ADO-sourced delivery decks
+-- devops/                DevOps and DORA metric decks
+-- team_topologies/       Org design decks
+-- architecture_overview.yaml  Root-level generic examples
+-- executive_update.yaml
+-- kpi_dashboard.yaml
+-- product_strategy.yaml
+-- weekly_ops_report.yaml
+-- catalog.yaml           Machine-readable example catalogue
+-- README.md
```

### When to modify what

| Task | Action |
|---|---|
| Browse examples | `pptgen example list` |
| Copy an example | `pptgen example copy <name> --output workspace/decks/<name>.yaml` |
| Add a new example | Create a YAML file in the appropriate library directory; validate it with `pptgen validate` |
| Fix an example | Edit the YAML; re-validate; ensure no coercion warnings |

**Rule:** All example YAML files must pass `pptgen validate` with no errors.

---

## Schemas (`schemas/`)

```
schemas/
|
+-- deck.schema.json       JSON Schema for deck YAML (portable contract)
+-- deck_patterns.yaml     Deck composition pattern definitions
```

These files are reference artifacts. `deck.schema.json` can be used by:
- IDEs for inline validation
- CI pipelines for pre-commit checks
- External tooling outside the Python engine

---

## Skills (`skills/`)

```
skills/
|
+-- README.md
+-- generate_pptgen_deck_yaml_skill.md   Claude skill: YAML generation
+-- validate_pptgen_deck_yaml_skill.md   Claude skill: YAML validation
+-- improve_pptgen_deck_yaml.md          Claude skill: deck improvement
```

These are Claude Code skill files. They are read directly by Claude when invoked. Modify them to change AI behaviour for deck generation, validation, or improvement.

---

## Documentation (`docs/`)

```
docs/
|
+-- ARCHITECTURE_MAP.md          Full architecture reference
+-- PROJECT_OVERVIEW.md          Platform overview
+-- architecture/
|   +-- authoring_contract.md    Canonical YAML authoring rules
|   +-- system_map.md            Engine + workspace + AI system maps
|   +-- pptgen_implementation_plan.md
+-- authoring/
|   +-- yaml_authoring_guide.md  Manual YAML authoring guide
|   +-- ai_generation_rules.md   AI generation constraints
|   +-- slide_type_reference.md  Per-type field reference
+-- ai-playbooks/
|   +-- routing_table.yaml       Input type → playbook routing table
|   +-- README.md                Playbook index
|   +-- *.md                     Individual playbook files
|   +-- examples/                End-to-end playbook worked examples
+-- workspace/
|   +-- workspace_model.md       Workspace directory reference
|   +-- workflow_runbook.md      Step-by-step workflow procedures
|   +-- quickstart.md            First-deck quickstart
+-- guides/
|   +-- how_decks_are_built.md   Pipeline walkthrough
|   +-- repository_guide.md      This file
+-- examples/
|   +-- example_index.md         Scenario → example mapping
+-- standards/
|   +-- deck_yaml_schema_specification.md
|   +-- template_authoring_standard.md
|   +-- template_validation_checklist.md
```

---

## Tests (`tests/`)

```
tests/
|
+-- fixtures/                Test YAML files
+-- unit/                    Unit tests per module
+-- integration/             Full pipeline tests against real files
```

Run the test suite:

```bash
pytest
pytest --tb=short -q    # quiet output
```

All tests must pass before committing changes.

---

## Do Not Modify

| File | Why |
|---|---|
| `pyproject.toml` entry point | Changing `pptgen.cli:app` breaks the installed CLI |
| `templates/registry.yaml` template paths | These are contract paths — the renderer resolves them at build time |
| Example files without re-validating | Examples are reference patterns used by AI workflows |

---

## Key Invariants

1. All example YAML files must pass `pptgen validate`.
2. All slide types must be registered in `slide_registry.py`.
3. Placeholder names in templates must be `UPPERCASE_SNAKE_CASE`.
4. Template IDs in the registry must be unique, even if backed by the same file.
5. The `extra='forbid'` Pydantic constraint must not be relaxed — it enforces the schema contract.
