# pptgen

**AI-Powered Presentation Generation Platform**

![Python](https://img.shields.io/badge/python-3.11+-blue)
![Status](https://img.shields.io/badge/status-internal--platform-purple)

`pptgen` converts raw text — meeting notes, sprint exports, ADR discussions, DevOps metrics — directly into PowerPoint presentations using template-driven rendering and an AI-assisted pipeline.

---

## Core Capabilities

- **Text-to-PowerPoint pipeline** — paste raw text, get a `.pptx` in one command
- **Automatic input routing** — input is classified and routed to the right playbook
- **Two execution modes** — `deterministic` (rule-based) and `ai` (LLM-assisted)
- **Template registry** — all output uses registered, approved `.pptx` templates
- **REST API** — `POST /v1/generate` for programmatic access
- **Web UI** — browser-based form for preview, generation, and download
- **Input connectors** — normalize structured sources (transcripts, ADO exports, metrics)
- **Batch generation** — process a directory of inputs in one command
- **Artifact export** — save intermediate pipeline objects (spec, plan, deck definition)
- **Preview mode** — plan slides without rendering a file

---

## Architecture

```
Input text  →  Router  →  Playbook  →  PresentationSpec
                                              ↓
                                        Slide Planner
                                              ↓
                                       Deck Definition
                                              ↓
                                    Renderer (python-pptx)
                                              ↓
                                         .pptx file
```

Interfaces: **CLI** · **REST API (`/v1`)** · **React Web UI**

See [docs/architecture/system_overview.md](docs/architecture/system_overview.md) for the full pipeline narrative.

---

## Quick Start

```bash
# Install
pip install -e .

# Generate a deck from a text file
pptgen generate notes/meeting.txt

# Generate with AI mode and save to a specific path
pptgen generate notes/sprint.txt --mode ai --output output/sprint.pptx

# Preview (plan slides without rendering)
pptgen generate notes/meeting.txt --preview
```

For full onboarding including the API and UI, see [docs/guides/getting_started.md](docs/guides/getting_started.md).

---

## Interfaces

### CLI

```bash
pptgen generate <file>           # Text → .pptx (full pipeline)
pptgen generate-batch <dir>      # Process a directory of inputs
pptgen ingest <type> <file>      # Preview connector normalization
pptgen build --input deck.yaml   # Render a pre-authored YAML deck
pptgen validate --input deck.yaml
pptgen list-templates
```

Full CLI reference: [docs/development/repository_guide.md](docs/development/repository_guide.md)

### API

```bash
uvicorn pptgen.api.server:app --reload   # Start on http://localhost:8000
```

Endpoints:

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/health` | Health check |
| GET | `/v1/templates` | List registered templates |
| GET | `/v1/playbooks` | List available playbooks |
| POST | `/v1/generate` | Run the generation pipeline |
| GET | `/v1/files/download` | Download a generated file |

Interactive docs: `http://localhost:8000/docs`

Full API reference: [docs/architecture/api_and_service_layer.md](docs/architecture/api_and_service_layer.md)

### Web UI

```bash
cd web && npm install && npm run dev     # Start on http://localhost:5173
```

Features: text input · mode/template selection · preview · generate · download · artifact paths

---

## Supported Slide Types

`title` · `section` · `bullets` · `two_column` · `metric_summary` · `image_caption`

See [docs/authoring/slide_type_reference.md](docs/authoring/slide_type_reference.md).

---

## Templates

Templates are registered in `templates/registry.yaml`. Currently approved:

- `ops_review_v1`
- `architecture_overview_v1`
- `executive_brief_v1`

See [docs/standards/template_authoring_standard.md](docs/standards/template_authoring_standard.md) to add a new template.

---

## Testing

```bash
pytest                        # Backend (957 tests)
cd web && npm test            # Frontend (64 tests)
```

---

## Documentation

| Document | Purpose |
|---|---|
| [docs/guides/getting_started.md](docs/guides/getting_started.md) | Start here — run the platform locally |
| [docs/architecture/system_overview.md](docs/architecture/system_overview.md) | Full platform architecture |
| [docs/architecture/api_and_service_layer.md](docs/architecture/api_and_service_layer.md) | API endpoints and contracts |
| [docs/development/repository_guide.md](docs/development/repository_guide.md) | Where code lives; how to extend |
| [docs/authoring/yaml_authoring_guide.md](docs/authoring/yaml_authoring_guide.md) | Manual YAML deck authoring |
| [docs/authoring/slide_type_reference.md](docs/authoring/slide_type_reference.md) | Slide type field reference |
| [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) | Deep-dive architecture reference |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guide |

---

## YAML Authoring (manual workflow)

For teams that prefer writing deck definitions directly in YAML:

```yaml
deck:
  title: DevOps Strategy
  author: David Harris
  template: ops_review_v1

slides:
  - type: title
    title: DevOps Transformation
    subtitle: 30-60-90 Day Plan

  - type: bullets
    title: Strategic Priorities
    bullets:
      - Stabilize production pipelines
      - Improve deployment consistency
```

```bash
pptgen validate --input deck.yaml
pptgen build --input deck.yaml --output strategy.pptx
```

Full guide: [docs/authoring/yaml_authoring_guide.md](docs/authoring/yaml_authoring_guide.md)
