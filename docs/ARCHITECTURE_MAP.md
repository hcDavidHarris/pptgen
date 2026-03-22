# pptgen Architecture Map

Version: 1.0
Owner: Analytics / DevOps Platform Team
Last Updated: 2026-03-22

This document is the authoritative internal architecture reference for the pptgen platform. It captures the system design, component responsibilities, pipeline mechanics, AI workflow routing, and known gaps. It is intended as a persistent mental model for contributors and AI development assistants.

---

## 1. Platform Purpose

`pptgen` is a **template-driven PowerPoint generation platform**. It converts structured YAML deck definitions into branded `.pptx` files using predefined PowerPoint templates.

Core principle: separate *what* (YAML content) from *how it looks* (template layouts) from *how it renders* (the engine). This enables repeatable, automated, and AI-assisted presentation creation.

---

## 2. Architecture Layers

| Layer | Location | Responsibility |
|---|---|---|
| Content | `*.yaml` deck files | Presentation structure and copy |
| Layout | `template/*.potx` / `.pptx` | Visual branding, typography, slide positions |
| Registry | `templates/registry.yaml` | Maps template IDs → file paths + metadata |
| Engine | `src/pptgen/` | YAML → PPTX rendering logic |
| Skills | `skills/*.md` | Claude-readable AI workflow instructions |
| Playbooks | `docs/ai-playbooks/` | Input-type → workflow routing instructions |
| Examples | `examples/` | Reference YAML patterns per use case |
| Workspace | Outside repo | Operational data, generated decks, output `.pptx` |

---

## 3. YAML → PPTX Pipeline

```
YAML file on disk
  ↓
yaml_loader.load_deck()
  → PyYAML parses raw dict
  → Pydantic DeckFile model validates (extra='forbid', discriminated union on `type`)
  → Returns (DeckFile, raw_dict)
  ↓
deck_validator.validate_deck()
  → Template ID exists in registry and is 'approved'
  → Slide IDs are unique
  → Semantic rules: max 4 metrics, bullet count warnings
  → Coercion warnings (unquoted numeric values in YAML)
  ↓
deck_renderer.render_deck()
  → template_loader opens .pptx via python-pptx
  → template_inspector maps layout names → SlideLayout objects
  → Per slide:
      - prs.slides.add_slide(layout)
      - rename placeholder shapes by idx → UPPERCASE_SNAKE_CASE canonical names
      - copy lstStyle from layout (colour inheritance fix for dark-bg master)
      - dispatch via SLIDE_RENDERERS[type] → renderer function
      - placeholder_mapper.set_text / set_bullets writes content by shape name
  → prs.save(output_path)
  ↓
output/<title>.pptx
```

---

## 4. Codebase Components

### Models (`src/pptgen/models/`)

| Model | Purpose |
|---|---|
| `DeckFile` | Top-level document; requires `deck` + `slides` keys; `extra='forbid'` |
| `DeckMetadata` | `title`, `template`, `author` required; `subtitle`, `version`, `date`, `status`, `tags` optional |
| `SlideUnion` | Discriminated union on `type` field — unsupported types fail at parse, not silently |
| `TitleSlide` | `type`, `title`, `subtitle` |
| `SectionSlide` | `type`, `section_title`, optional `section_subtitle` |
| `BulletsSlide` | `type`, `title`, `bullets` (non-empty list) |
| `TwoColumnSlide` | `type`, `title`, `left_content`, `right_content` |
| `MetricSummarySlide` | `type`, `title`, `metrics` (1–4 `MetricItem`) |
| `ImageCaptionSlide` | `type`, `title`, `image_path`, `caption` |
| `MetricItem` | `label`, `value` (always string, coerced), optional `unit` |

All slide models share optional base fields: `id`, `notes`, `visible`.

### Loader (`src/pptgen/loaders/yaml_loader.py`)

- `load_deck(path)` → `(DeckFile, raw_dict)`
- The raw dict travels alongside the typed model so the validator can detect YAML type coercions (e.g. unquoted `99.9` parsed as float) and emit warnings rather than errors.

### Validator (`src/pptgen/validators/deck_validator.py`)

- Returns `ValidationResult(valid, errors, warnings)` — never raises, always reportable.
- Hard errors: unregistered template, non-unique slide IDs, >4 metrics per slide.
- Warnings: non-approved template status, >6 bullets, single metric on a metric slide, label >40 chars, composed value >20 chars.

### Registry (`src/pptgen/registry/registry.py`)

- `TemplateRegistry.from_file()` loads `templates/registry.yaml`.
- `TemplateEntry` fields: `template_id`, `version`, `owner`, `status`, `path`, `supported_slide_types`, `max_metrics`.
- Uses `extra='ignore'` — forward-compatible with new registry fields.

### Renderer (`src/pptgen/render/`)

| Module | Responsibility |
|---|---|
| `deck_renderer.py` | Orchestration: load → inspect → iterate slides → dispatch → save |
| `slide_renderers.py` | `SLIDE_RENDERERS` dict; one pure function per slide type; no styling logic |
| `placeholder_mapper.py` | Finds shapes by `UPPERCASE_SNAKE_CASE` name; `set_text` / `set_bullets` |
| `template_inspector.py` | Maps layout names → `SlideLayout` objects |
| `template_loader.py` | Opens `.pptx` via python-pptx |

**Key internal detail:** python-pptx resets placeholder shape names on `add_slide()`. `deck_renderer.py` immediately renames them using `_SLIDE_TYPE_PH_NAMES` (a dict of `placeholder_format.idx → canonical_name`) to restore the `UPPERCASE_SNAKE_CASE` contract before dispatching to renderers.

### CLI (`src/pptgen/cli.py`)

Built with Typer.

| Command | Effect |
|---|---|
| `pptgen build --input deck.yaml [--output path.pptx]` | Validate then render |
| `pptgen validate --input deck.yaml` | Validate only, no render |
| `pptgen list-templates` | List all registry entries with status and version |

Output defaults to `output/<safe-title>.pptx`.

### Errors (`src/pptgen/errors/__init__.py`)

```
PptgenError
├── YAMLLoadError          file unreadable or malformed YAML
├── ParseError             content fails Pydantic schema
├── RegistryError          registry file unreadable or malformed
├── TemplateLoadError      .pptx file cannot be opened
└── TemplateCompatibilityError  required layout or placeholder missing
```

---

## 5. Template Placeholder Contract

All placeholder names are `UPPERCASE_SNAKE_CASE`. Template layout names must match exactly.

| Slide Type | Layout Name | Placeholders |
|---|---|---|
| `title` | Title Layout | `TITLE`, `SUBTITLE` |
| `section` | Section Layout | `SECTION_TITLE`, `SECTION_SUBTITLE` |
| `bullets` | Bullets Layout | `TITLE`, `BULLETS` |
| `two_column` | Two Column Layout | `TITLE`, `LEFT_CONTENT`, `RIGHT_CONTENT` |
| `metric_summary` | Metric Summary Layout | `TITLE`, `METRIC_1_LABEL`, `METRIC_1_VALUE` … `METRIC_4_LABEL`, `METRIC_4_VALUE` (9 total, 2×2 grid) |
| `image_caption` | Image Caption Layout | `TITLE`, `IMAGE`, `CAPTION` |

Metric rendering: `value + unit` (direct concatenation). Authors embed any separator in the `unit` string (e.g. `unit: " ms"`).

Unused metric positions are cleared to empty string so template default text does not bleed through.

---

## 6. Template Registry Contract

File: `templates/registry.yaml`

```yaml
templates:
  - template_id: ops_review_v1
    version: "1.0"
    owner: Analytics Services
    status: approved          # only 'approved' is recommended for production
    path: template/HC_Powerpoint_Template_with_pptgen_placeholders.potx
    supported_slide_types:
      - title
      - section
      - bullets
      - two_column
      - metric_summary
      - image_caption
```

The validator checks that `deck.template` resolves to a registered entry and that its `status` is `approved`. Non-approved templates generate a warning, not an error.

---

## 7. Workspace Model

The workspace lives **outside the pptgen repository**. The repo provides the engine, templates, and examples. Operational data stays local.

```
workspace/
├─ ado_exports/   ← raw ADO query exports, CSVs, JSON
├─ notes/         ← summaries, meeting notes, AI-generated digests
├─ decks/         ← generated pptgen YAML deck files
└─ output/        ← rendered .pptx files
```

End-to-end flow:

```
Azure DevOps data → ado_exports/ → notes/ → decks/ → pptgen build → output/
```

---

## 8. AI Skills

| Skill file | Role | When to use |
|---|---|---|
| `skills/generate_pptgen_deck_yaml_skill.md` | Convert notes/outlines → valid YAML | Starting from scratch |
| `skills/validate_pptgen_deck_yaml_skill.md` | Schema + semantic validation | After generate, before build |
| `skills/improve_pptgen_deck_yaml.md` | Refine slide quality, titles, flow | Between validate passes |

Default template when not specified: `ops_review_v1`.

Standard AI-assisted workflow:

```
notes → generate → validate → improve → validate → pptgen build → .pptx
```

---

## 9. AI Routing Table

File: `docs/ai-playbooks/routing_table.yaml`

When a user provides raw input for deck generation, match input type against this table to select the correct playbook and example pattern.

| Route ID | Input Types | Playbook | Example Pattern | Output |
|---|---|---|---|---|
| `meeting_notes_to_eos_rocks` | meeting_notes, leadership_summary, quarterly_planning_notes | `docs/ai-playbooks/meeting-notes-to-eos-rocks.md` | `examples/eos/eos_rocks.yaml` | `workspace/decks/eos_rocks.yaml` |
| `ado_summary_to_weekly_delivery` | ado_export_summary, sprint_summary, delivery_status_summary, backlog_summary | `docs/ai-playbooks/ado-summary-to-weekly-delivery.md` | `examples/engineering_delivery/weekly_delivery_update.yaml` | `workspace/decks/weekly_delivery_update.yaml` |
| `architecture_notes_to_adr_deck` | architecture_notes, adr_summary, design_review_notes, system_design_notes | `docs/ai-playbooks/architecture-notes-to-adr-deck.md` | `examples/architecture/adr_template.yaml` | `workspace/decks/adr_review.yaml` |
| `devops_metrics_to_scorecard` | devops_metrics, dora_metrics, cicd_metrics, reliability_metrics | `docs/ai-playbooks/devops-metrics-to-scorecard.md` | `examples/devops/devops_metrics.yaml` | `workspace/decks/devops_metrics.yaml` |

**Routing rules:**
1. Match input to closest route by `input_type` and `tags`.
2. Always use the referenced `example_pattern` as the structural template.
3. Generate YAML before rendering.
4. Validate before build.
5. Prefer concise, presentation-friendly output.

**Default behaviour:** If no route matches, choose the closest example library and use `generate_pptgen_deck_yaml` for a first draft, then validate and build.

---

## 10. Example Libraries

| Library | Organizational Workflow | Key Patterns |
|---|---|---|
| `examples/eos/` | EOS quarterly rocks, scorecard, VTO, issues list | `bullets`, `two_column`, `metric_summary` |
| `examples/engineering_delivery/` | Weekly delivery, sprint summaries, backlog health, risks | `bullets`, `metric_summary` |
| `examples/devops/` | DORA metrics, DevOps Three Ways, pipeline reviews | `metric_summary`, `bullets`, `section` |
| `examples/team_topologies/` | Team types, interaction modes, cognitive load, platform team model | `bullets`, `two_column`, `section` |
| Root-level | Generic executive, architecture overview, KPI, ops, strategy | All types |

---

## 11. System Map

```
AUTHOR WORKFLOW
────────────────────────────────────────────────────────────────
Ideas / notes
  → manually write deck.yaml  (use examples/ as structural patterns)
  → pptgen validate --input deck.yaml    ← catch errors before rendering
  → pptgen build --input deck.yaml
  → output/<title>.pptx


AI-ASSISTED WORKFLOW
────────────────────────────────────────────────────────────────
Raw input (ADO export / meeting notes / metrics / arch notes)
  → consult routing_table.yaml           ← select playbook + example pattern
  → generate_pptgen_deck_yaml (skill)    → workspace/decks/*.yaml
  → validate_pptgen_deck_yaml (skill)    ← fix any errors
  → improve_pptgen_deck_yaml (skill)     ← refine quality
  → validate_pptgen_deck_yaml (skill)    ← confirm clean
  → pptgen build --input workspace/decks/*.yaml
  → workspace/output/*.pptx


ENGINE RENDERING WORKFLOW
────────────────────────────────────────────────────────────────
deck.yaml
  → load_deck()          PyYAML + Pydantic strict validation
  → validate_deck()      registry check + semantic rules → ValidationResult
  → render_deck()        template_loader
                           → template_inspector (layout name map)
                           → per slide: add_slide + rename placeholders
                                        + copy lstStyle (colour fix)
                                        + SLIDE_RENDERERS dispatch
                                        + placeholder_mapper writes text
  → prs.save()
  → deck.pptx
```

---

## 12. How to Extend: Adding a New Slide Type

Adding a new slide type requires changes in five places:

1. **`src/pptgen/models/slides.py`** — add a new `*Slide` model class and add it to `SlideUnion`.
2. **`src/pptgen/render/slide_renderers.py`** — add a `render_*_slide()` function and register it in `SLIDE_RENDERERS`.
3. **`src/pptgen/render/deck_renderer.py`** — add the layout name to `SLIDE_TYPE_TO_LAYOUT` and the placeholder idx map to `_SLIDE_TYPE_PH_NAMES`.
4. **Template `.potx` file** — add a matching layout with the correct `UPPERCASE_SNAKE_CASE` placeholder names.
5. **`templates/registry.yaml`** — add the new type to `supported_slide_types` for relevant templates.

---

## 13. Known Gaps and Future Opportunities

### Active Gaps

| Gap | Location | Impact |
|---|---|---|
| `image_caption` renderer not registered | `slide_renderers.py` — missing entry in `SLIDE_RENDERERS` | Any deck with `image_caption` slides fails at render with `KeyError` |
| `examples/architecture/` directory missing | Referenced in `routing_table.yaml` as `examples/architecture/adr_template.yaml` | ADR route has no example pattern to follow |

### CLI Opportunities

- `pptgen init-workspace` — scaffold the workspace directory structure (already documented in `docs/workspace-pattern.md`)
- `pptgen list-examples` / `pptgen show-example <name>` — browse example library from CLI (already planned in `examples/README.md`)
- `pptgen ai generate <playbook-name>` — invoke a routing table playbook directly from the CLI

### AI Workflow Opportunities

- Auto-routing: accept raw input and resolve the correct playbook automatically without requiring the user to name it
- `pptgen ai route --input file.txt` — CLI command that returns the matched route from `routing_table.yaml`
- ADO integration skill — pull from ADO API directly into notes format, removing manual export step

### Validation Opportunities

- Template compatibility pre-check: verify all required layouts and placeholders exist in the `.pptx` before processing any slides
- JSON Schema export from Pydantic models for use in external editors and CI lint steps

### Template Opportunities

- Second template variant (e.g. `executive_brief_v1`) — all examples currently reference `ops_review_v1`, creating a single point of failure
- 6-metric grid layout for expanded KPI slides
- Agenda slide layout
