# pptgen — System Overview

Version: 2.0
See also: [ARCHITECTURE_MAP.md](../../ARCHITECTURE_MAP.md) for the deep-dive reference.

---

## Platform Overview

pptgen is a multi-interface presentation generation platform. Raw text (meeting notes,
sprint exports, architecture decisions, DevOps metrics) is routed through a structured
pipeline that classifies the input, extracts content, plans slides, and renders a
PowerPoint file using approved templates.

Three interfaces share a single backend pipeline:

```
CLI  ──────────────────────────────────────────────┐
                                                   ↓
API (/v1)  ────────────────────────────────→  Pipeline  →  .pptx
                                                   ↑
React UI  ─────────────────────────────────────────┘
```

---

## Generation Pipeline

```
Input text
    │
    ▼
Input Router  (src/pptgen/input_router/)
    │   Classifies text → selects playbook_id
    │   Routing rules: src/pptgen/input_router/routing_table.yaml
    │
    ▼
Playbook Execution  (src/pptgen/playbook_engine/)
    │   mode=deterministic → deterministic_executor.py
    │   mode=ai            → ai_executor.py  (LLM via model_factory.py)
    │   Returns: PresentationSpec
    │
    ▼
Slide Planner  (src/pptgen/planner/)
    │   Converts PresentationSpec → SlidePlan
    │   Applies planning rules (slide count, type selection)
    │
    ▼
Spec-to-Deck Translator  (src/pptgen/spec/spec_to_deck.py)
    │   Converts SlidePlan → deck_definition dict
    │
    ├──► [optional] Artifact Export  (src/pptgen/artifacts/)
    │       spec.json, slide_plan.json, deck_definition.json
    │
    ▼
Renderer  (src/pptgen/render/)
    │   Loads template .pptx  →  maps layouts  →  writes placeholders
    │   Returns: .pptx file
    │
    ▼
PipelineResult  (stage="rendered" | "deck_planned")
```

`output_path=None` (preview mode) stops the pipeline after planning — no file is written.

---

## Pipeline Stages

| Stage | Module | Output |
|---|---|---|
| Route input | `input_router/` | `playbook_id` |
| Execute playbook | `playbook_engine/` | `PresentationSpec` |
| Plan slides | `planner/` | `SlidePlan` |
| Translate to deck | `spec/spec_to_deck.py` | `deck_definition` dict |
| Export artifacts | `artifacts/` | JSON files (optional) |
| Render | `render/` | `.pptx` file |

---

## Interfaces

### CLI

Entry point: `pptgen` (installed via `pyproject.toml`)

Key commands:

| Command | Purpose |
|---|---|
| `pptgen generate <file>` | Full text-to-PPTX pipeline |
| `pptgen generate-batch <dir>` | Process directory of inputs |
| `pptgen ingest <type> <file>` | Preview connector normalization |
| `pptgen build --input deck.yaml` | Render a manually authored YAML deck |
| `pptgen validate --input deck.yaml` | Validate YAML without rendering |
| `pptgen list-templates` | List registered templates |

### REST API

Base: `http://localhost:8000`
Router prefix: `/v1`
Docs: `http://localhost:8000/docs`

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/health` | Health check |
| GET | `/v1/templates` | Registered template IDs |
| GET | `/v1/playbooks` | Available playbook IDs |
| POST | `/v1/generate` | Run pipeline (preview or full) |
| GET | `/v1/files/download` | Download generated `.pptx` |

Every response includes a `request_id` (UUID4) for tracing.
See [api_and_service_layer.md](api_and_service_layer.md) for full contracts.

### Web UI

Location: `web/`
Technology: React + TypeScript + Vite
Dev server: `http://localhost:5173`

Features:
- Text input for raw notes/data
- Mode selector (`deterministic` / `ai`)
- Template dropdown (populated from `/v1/templates`)
- Preview mode (plan only — no file rendered)
- Full generation with download link
- Artifact path display
- `request_id` display with copy button

---

## Connectors

Connectors normalize structured source files into pipeline-ready text before
the input router classifies them.

Located in `src/pptgen/connectors/`:

| Type | Class | Input | Routes to |
|---|---|---|---|
| `transcript` | `TranscriptConnector` | Meeting transcript text | `meeting-notes-to-eos-rocks` |
| `ado` | `ADOConnector` | Azure DevOps sprint JSON | `ado-summary-to-weekly-delivery` |
| `metrics` | `MetricsConnector` | DORA/DevOps metrics JSON | `devops-metrics-to-scorecard` |

Usage:
```bash
pptgen ingest ado sprint_export.json
pptgen generate-batch ./exports/ --connector ado
```

---

## Execution Modes

| Mode | Behaviour |
|---|---|
| `deterministic` | Rule-based content extraction. No external calls. Fully reproducible. |
| `ai` | LLM-assisted content generation via `ai_executor.py`. Currently uses `MockModel`. |

The active model is resolved by `src/pptgen/ai/models/model_factory.py`. Real provider
adapters (OpenAI, Anthropic, Ollama) are registered as stubs and ready to implement.

---

## Artifacts

When `artifacts=True` (CLI flag `--artifacts` or API field), three JSON files are
written alongside the output:

| File | Content | Source |
|---|---|---|
| `spec.json` | `PresentationSpec` dump | Pydantic `model_dump()` |
| `slide_plan.json` | `SlidePlan` dump | `dataclasses.asdict()` |
| `deck_definition.json` | Deck YAML dict | Plain Python dict |

Default location: `<output_stem>.artifacts/` adjacent to the `.pptx`.

---

## Templates

Templates are registered in `templates/registry.yaml`.
Each entry names a `.potx` file and its supported slide types.

Currently registered: `ops_review_v1`, `architecture_overview_v1`, `executive_brief_v1`

Placeholder naming convention: `UPPERCASE_SNAKE_CASE`
Template lifecycle: `draft` → `approved` → `deprecated`

See [docs/standards/template_authoring_standard.md](../standards/template_authoring_standard.md).

---

## Key Data Models

Full field-level reference: [docs/architecture/data_models.md](data_models.md)

| Model | Purpose | Source |
|---|---|---|
| `PresentationSpec` | Semantic content extracted from input text | `spec/presentation_spec.py` |
| `SlidePlan` | Planning summary — slide count and types | `planner/slide_plan.py` |
| `deck_definition` | Structural deck dict consumed by the renderer | `spec/spec_to_deck.py` |
| `PipelineResult` | Aggregate result returned by `generate_presentation()` | `pipeline/generation_pipeline.py` |
| `ConnectorOutput` | Normalised text + metadata from a connector | `connectors/base_connector.py` |
| `BatchResult` | Aggregate result for a `generate-batch` run | `orchestration/batch_generator.py` |

---

## Extension Points

| Task | Where |
|---|---|
| Add a connector | `src/pptgen/connectors/` + `connector_factory.py` |
| Add a playbook route | `src/pptgen/input_router/routing_table.yaml` + playbook docs |
| Add a template | `templates/` + `templates/registry.yaml` |
| Add an execution mode | `src/pptgen/playbook_engine/execution_strategy.py` |
| Add an API endpoint | `src/pptgen/api/routes.py` + `schemas.py` |
| Add a slide type | `src/pptgen/render/slide_renderers.py` + `slide_registry.py` |

Full step-by-step: [docs/development/repository_guide.md](../../docs/development/repository_guide.md)
