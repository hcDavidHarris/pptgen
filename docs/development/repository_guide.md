# Repository Guide — Developer Navigation

Version: 2.0
See also: [docs/guides/repository_guide.md](../../docs/guides/repository_guide.md) for the YAML-authoring-focused content guide.

---

## Source Layout

```
src/pptgen/
├── api/             FastAPI server, routes, schemas, file download
├── artifacts/       Pipeline artifact export (spec, plan, deck definition JSON)
├── cli/             Typer CLI commands
├── connectors/      Input connectors (transcript, ado, metrics)
├── errors/          PptgenError exception hierarchy
├── input_router/    Input classification → playbook_id selection
├── models/          Pydantic deck/slide models (YAML authoring layer)
├── pipeline/        Main generation pipeline orchestrator
├── planner/         SlidePlan construction from PresentationSpec
├── playbook_engine/ Deterministic and AI playbook executors
├── render/          python-pptx rendering (deck, slides, placeholders)
├── spec/            PresentationSpec model + spec-to-deck translator
├── validators/      YAML deck semantic validation
└── registry/        Template registry loader
```

---

## CLI — `src/pptgen/cli/`

Entry point registered in `pyproject.toml` as `pptgen`.

| File | Command(s) |
|---|---|
| `__init__.py` | `pptgen build`, `pptgen validate`, `pptgen list-templates` |
| `generate.py` | `pptgen generate <file>` |
| `generate_batch.py` | `pptgen generate-batch <dir>` |
| `ingest.py` | `pptgen ingest <type> <file>` |
| `deck_scaffold.py` | `pptgen deck scaffold` |
| `template_inspect.py` | `pptgen template inspect` |
| `example_commands.py` | `pptgen example list/show/copy` |
| `workspace_init.py` | `pptgen workspace init` |
| `validation_explain.py` | `--explain` flag support for `validate` |

---

## API — `src/pptgen/api/`

| File | Role |
|---|---|
| `server.py` | FastAPI app, CORS middleware, router registration |
| `routes.py` | `/v1/health`, `/v1/templates`, `/v1/playbooks`, `/v1/generate` |
| `file_routes.py` | `/v1/files/download` — serves generated `.pptx` files |
| `schemas.py` | Pydantic request/response models |
| `service.py` | Business logic delegated to from routes |

Start: `uvicorn pptgen.api.server:app --reload`
Docs: `http://localhost:8000/docs`

---

## Pipeline — `src/pptgen/pipeline/generation_pipeline.py`

`generate_presentation(text, mode, template_id, artifacts, output_path)` runs these stages in sequence:

1. Route input → `input_router/` → `playbook_id`
2. Execute playbook → `playbook_engine/` → `PresentationSpec`
3. Plan slides → `planner/` → `SlidePlan`
4. Translate to deck → `spec/spec_to_deck.py` → `deck_definition` dict
5. Export artifacts → `artifacts/artifact_writer.py` (if enabled)
6. Render → `render/deck_renderer.py` → `.pptx` file

Returns `PipelineResult` with `stage`, `output_path`, `artifact_paths`, etc.
`output_path=None` stops after stage 4 (preview mode).

---

## Connectors — `src/pptgen/connectors/`

| File | Type | Input format |
|---|---|---|
| `transcript_connector.py` | `transcript` | Meeting transcript text |
| `ado_connector.py` | `ado` | Azure DevOps sprint JSON |
| `metrics_connector.py` | `metrics` | DORA/DevOps metrics JSON |
| `connector_factory.py` | — | Factory: `type → connector instance` |
| `base_connector.py` | — | `BaseConnector` ABC, `ConnectorOutput` |

---

## Playbook Engine — `src/pptgen/playbook_engine/`

| File | Role |
|---|---|
| `execution_strategy.py` | `ExecutionStrategy` ABC; dispatches to deterministic or AI executor |
| `deterministic_executor.py` | Rule-based content extraction — no external calls |
| `ai_executor.py` | LLM-assisted generation via `ai/models/model_factory.py` |

The active model is resolved by `model_factory.py`. Real provider adapters
(OpenAI, Anthropic, Ollama) are registered as stubs ready to implement.

---

## Artifacts — `src/pptgen/artifacts/artifact_writer.py`

When `artifacts=True`, writes three JSON files to `<output_stem>.artifacts/`:

| File | Content |
|---|---|
| `spec.json` | `PresentationSpec` (Pydantic `model_dump()`) |
| `slide_plan.json` | `SlidePlan` (`dataclasses.asdict()`) |
| `deck_definition.json` | Deck dict passed to the renderer |

---

## Rendering — `src/pptgen/render/`

| File | Role |
|---|---|
| `deck_renderer.py` | Orchestrates slide loop, loads template, writes output |
| `slide_renderers.py` | Per-type render functions (`SLIDE_RENDERERS` dispatch dict) |
| `placeholder_mapper.py` | Resolves placeholder names → shape objects in the template |

---

## Web UI — `web/src/`

| File | Role |
|---|---|
| `App.tsx` | Root state management, API calls, layout |
| `api.ts` | Typed wrappers for `/v1/templates`, `/v1/generate`, download URL |
| `types.ts` | TypeScript types: `GenerateRequest`, `GenerateResponse`, `ApiError` |
| `components/GenerateForm.tsx` | Text input, mode/template selectors, Preview/Generate buttons |
| `components/ResultPanel.tsx` | Result display: stage, slide count, output path, download link |
| `components/StatusBanner.tsx` | Loading spinner and error alert |

Dev server: `cd web && npm run dev` → `http://localhost:5173`
Config: `web/.env` — set `VITE_API_BASE_URL` to point at a remote API.

---

## Tests

```
tests/
├── unit/              Per-module unit tests (all fast, no file I/O)
├── integration/       Full render pipeline tests (write real .pptx)
├── test_spec_layer.py
├── test_example_validation.py
└── test_image_caption_render.py

web/src/__tests__/     Frontend Vitest tests
```

```bash
pytest                  # All backend tests
cd web && npm test      # Frontend tests
```

---

## Where to Change What

| Task | File(s) |
|---|---|
| Add a connector | `src/pptgen/connectors/<type>_connector.py` + `connector_factory.py` |
| Add a template | `templates/<id>/` + `templates/registry.yaml` |
| Add an API endpoint | `src/pptgen/api/routes.py` + `schemas.py` + `service.py` |
| Add an execution mode | `src/pptgen/playbook_engine/execution_strategy.py` |
| Add a playbook route | `src/pptgen/input_router/routing_table.yaml` + playbook docs |
| Add a slide type | `src/pptgen/render/slide_renderers.py` + `slide_registry.py` |
| Add a CLI command | `src/pptgen/cli/<module>.py` + register in `cli/__init__.py` |
| Update UI | `web/src/` |
