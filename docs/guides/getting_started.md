# Getting Started with pptgen

A practical guide to running the platform from scratch.

---

## Prerequisites

- Python 3.11+
- Node 18+ (only needed for the Web UI)

```bash
pip install -e .          # Install pptgen and all Python dependencies
pptgen --help             # Verify the CLI is working
```

---

## 1. Generate a Deck from the CLI

Paste or save raw text (meeting notes, sprint exports, etc.) to a file, then run:

```bash
pptgen generate notes/meeting.txt
```

Generates a `.pptx` in the current directory.

Common options:

```bash
pptgen generate notes/sprint.txt --mode ai --output output/sprint.pptx
pptgen generate notes/meeting.txt --preview          # Plan slides, no file written
pptgen generate notes/meeting.txt --artifacts        # Also export spec/plan JSON files
```

---

## 2. Start the REST API

```bash
uvicorn pptgen.api.server:app --reload
```

API is available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

Quick health check:

```bash
curl http://localhost:8000/v1/health
```

---

## 3. Start the Web UI

```bash
cd web
npm install
npm run dev
```

UI is available at `http://localhost:5173`.

The UI talks to the API at `http://localhost:8000` via Vite's proxy.
To point it at a remote API, set `VITE_API_BASE_URL` in `web/.env`.

---

## 4. Preview Without Rendering

Preview mode plans the slide layout without writing a file. Useful for checking
what the pipeline will produce before committing.

**CLI:**
```bash
pptgen generate notes/meeting.txt --preview
```

**API:**
```bash
curl -X POST http://localhost:8000/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Meeting notes...", "preview_only": true}'
```

Response `stage` will be `"deck_planned"` and `output_path` will be `null`.

---

## 5. Use a Connector

Connectors normalize structured source files (ADO exports, transcripts, metrics)
into pipeline-ready text before routing.

```bash
pptgen ingest ado sprint_export.json        # Preview normalized ADO output
pptgen ingest transcript meeting.txt        # Preview transcript normalization
pptgen ingest metrics devops.json           # Preview metrics normalization
```

To generate a deck directly from a structured source:

```bash
pptgen generate sprint_export.json --connector ado
```

---

## 6. Batch Generation

Process a directory of inputs in one command:

```bash
pptgen generate-batch ./inputs/
pptgen generate-batch ./exports/ --connector ado --output-dir ./output/
```

Each input file produces a separate `.pptx` in the output directory.

---

## 7. Run Tests

```bash
pytest                          # All backend tests
cd web && npm test              # Frontend tests
```

---

## Next Steps

| What | Where |
|---|---|
| Full platform architecture | [docs/architecture/system_overview.md](../architecture/system_overview.md) |
| API endpoints and contracts | [docs/architecture/api_and_service_layer.md](../architecture/api_and_service_layer.md) |
| Developer guide (where code lives) | [docs/development/repository_guide.md](../../docs/development/repository_guide.md) |
| Manual YAML deck authoring | [docs/authoring/yaml_authoring_guide.md](../authoring/yaml_authoring_guide.md) |
| Slide type reference | [docs/authoring/slide_type_reference.md](../authoring/slide_type_reference.md) |
