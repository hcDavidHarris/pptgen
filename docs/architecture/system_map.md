# pptgen System Map

Version: 1.0
Owner: Analytics / DevOps Platform Team

> **Note:** This document covers the workspace and AI-assisted authoring workflow.
> For the full platform architecture (CLI pipeline, FastAPI service, Web UI, connectors),
> see [docs/architecture/system_overview.md](system_overview.md).

This document provides a concise system map of the pptgen platform across three dimensions: the engine architecture, the workspace architecture, and the AI-assisted workflow architecture.

---

## 1. Engine Architecture

```
YAML Deck File
    |
    | yaml_loader.load_deck(path)
    |   - PyYAML: parse raw dict
    |   - Pydantic DeckFile: validate schema (extra='forbid')
    |   - Returns: (DeckFile, raw_dict)
    |
    v
DeckFile + raw_dict
    |
    | deck_validator.validate_deck(deck, registry, raw_data)
    |   - registry check: template_id registered + approved
    |   - slide ID uniqueness
    |   - metric_summary: max 4 metrics (from SLIDE_TYPE_REGISTRY)
    |   - bullets: >6 warning (from SLIDE_TYPE_REGISTRY)
    |   - coercion warnings (from raw_dict comparison)
    |   - Returns: ValidationResult(valid, errors, warnings)
    |
    v
ValidationResult
    |
    | [if valid]
    |
    | deck_renderer.render_deck(deck, template_path, output_path)
    |   - template_loader: open .pptx
    |   - template_inspector: map layout names -> SlideLayout
    |   - per slide:
    |       add_slide(layout)
    |       rename placeholders (idx -> UPPERCASE_SNAKE_CASE)
    |       copy lstStyle (colour inheritance fix)
    |       SLIDE_RENDERERS[slide.type](model, pptx_slide)
    |           placeholder_mapper.set_text / set_bullets
    |   - prs.save(output_path)
    |
    v
output/<title>.pptx
```

### Engine Modules

| Module | Path | Role |
|---|---|---|
| CLI | `src/pptgen/cli/` | Entry point; command routing |
| Models | `src/pptgen/models/` | Pydantic schema; DeckFile + SlideUnion |
| Loader | `src/pptgen/loaders/` | YAML file reading + Pydantic parsing |
| Validator | `src/pptgen/validators/` | Semantic rules + ValidationResult |
| Registry | `src/pptgen/registry/` | Template registry loader |
| Slide Registry | `src/pptgen/slide_registry.py` | Slide type metadata; single source of truth |
| Renderer | `src/pptgen/render/` | PPTX orchestration + slide dispatch |
| Template Contract Validator | `src/pptgen/template_contract_validator.py` | Verifies .pptx layouts match contract |
| Errors | `src/pptgen/errors/` | Custom exception hierarchy |

---

## 2. Workspace Architecture

```
Azure DevOps / External Systems
    |
    | manual export or API
    v
workspace/ado_exports/          <- raw CSVs, JSONs
    |
    | manual summary or AI
    v
workspace/notes/                <- sprint summaries, meeting notes
    |
    | AI generation (generate_pptgen_deck_yaml skill)
    | OR manual authoring
    v
workspace/decks/                <- pptgen YAML deck files
    |
    | pptgen validate --input
    v
workspace/validated/            <- optional staging (validated decks)
    |
    | pptgen build --input
    v
workspace/output/               <- .pptx presentation files
```

### Workspace Directory Contract

| Directory | Contains | Source |
|---|---|---|
| `ado_exports/` | ADO query exports, CSVs, JSON | Azure DevOps or other systems |
| `notes/` | Human-readable or AI summaries | Meeting notes, AI-generated digests |
| `decks/` | pptgen YAML deck definitions | AI-generated or manually authored |
| `validated/` | Decks that passed `pptgen validate` | Optional staging area |
| `output/` | Generated .pptx files | `pptgen build` |

---

## 3. AI-Assisted Workflow Architecture

```
Raw Input
(ADO export / meeting notes / metrics / architecture notes)
    |
    | 1. Identify input type
    | 2. Consult routing_table.yaml
    v
Routing Decision
    |
    +-- input: ado_export_summary, sprint_summary
    |       route: ado_summary_to_weekly_delivery
    |       pattern: examples/engineering_delivery/weekly_delivery_update.yaml
    |
    +-- input: meeting_notes, quarterly_planning_notes
    |       route: meeting_notes_to_eos_rocks
    |       pattern: examples/eos/eos_rocks.yaml
    |
    +-- input: architecture_notes, adr_summary
    |       route: architecture_notes_to_adr_deck
    |       pattern: examples/architecture/adr_template.yaml
    |
    +-- input: devops_metrics, dora_metrics
    |       route: devops_metrics_to_scorecard
    |       pattern: examples/devops/devops_metrics.yaml
    |
    +-- no match
            use closest example; apply generate_pptgen_deck_yaml
    |
    v
generate_pptgen_deck_yaml (Claude skill)
    |
    | Applies: docs/authoring/ai_generation_rules.md
    | Uses:    selected example pattern as structural guide
    v
workspace/decks/<name>.yaml
    |
    v
validate_pptgen_deck_yaml (Claude skill)
    |
    | OR: pptgen validate --input workspace/decks/<name>.yaml
    v
[PASS] improve_pptgen_deck_yaml (Claude skill)  [optional]
    |
    v
validate_pptgen_deck_yaml (Claude skill)
    |
    v
pptgen build --input workspace/decks/<name>.yaml
    |
    v
workspace/output/<name>.pptx
```

### AI Workflow Files

| File | Role |
|---|---|
| `docs/ai-playbooks/routing_table.yaml` | Maps input type → playbook → example pattern |
| `docs/ai-playbooks/README.md` | Playbook index and workflow description |
| `docs/ai-playbooks/meeting-notes-to-eos-rocks.md` | EOS rocks playbook |
| `docs/ai-playbooks/ado-summary-to-weekly-delivery.md` | Weekly delivery playbook |
| `docs/ai-playbooks/architecture-notes-to-adr-deck.md` | ADR review playbook |
| `docs/ai-playbooks/devops-metrics-to-scorecard.md` | DevOps metrics playbook |
| `skills/generate_pptgen_deck_yaml_skill.md` | Claude skill: generate YAML |
| `skills/validate_pptgen_deck_yaml_skill.md` | Claude skill: validate YAML |
| `skills/improve_pptgen_deck_yaml.md` | Claude skill: improve deck quality |
| `docs/authoring/ai_generation_rules.md` | Rules Claude must follow when generating YAML |

---

## 4. Full Platform Map

```
pptgen Repository
|
+-- src/pptgen/           ENGINE
|   +-- cli/              CLI commands
|   +-- models/           Pydantic schema
|   +-- loaders/          YAML loader
|   +-- validators/       Semantic validator
|   +-- registry/         Template registry loader
|   +-- render/           PPTX renderer
|   +-- slide_registry.py Slide type metadata
|   +-- template_contract_validator.py
|   +-- errors/
|
+-- templates/            TEMPLATES
|   +-- registry.yaml     Template registry
|   +-- ops_review_v1/    Template files
|   +-- executive_brief_v1/
|   +-- architecture_overview_v1/
|
+-- examples/             EXAMPLE LIBRARY
|   +-- eos/
|   +-- engineering_delivery/
|   +-- devops/
|   +-- team_topologies/
|   +-- *.yaml            Root-level examples
|
+-- schemas/              SCHEMA ARTIFACTS
|   +-- deck.schema.json  JSON Schema (for external tooling)
|   +-- deck_patterns.yaml Deck composition patterns
|
+-- skills/               CLAUDE SKILLS
+-- docs/                 DOCUMENTATION
    +-- architecture/
    +-- authoring/
    +-- ai-playbooks/
    +-- workspace/
    +-- guides/
    +-- examples/

External (workspace)
+-- ado_exports/
+-- notes/
+-- decks/
+-- validated/
+-- output/
```
