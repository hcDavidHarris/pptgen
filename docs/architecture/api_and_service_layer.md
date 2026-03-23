# API and Service Layer

Version: 1.0
Base URL: `http://localhost:8000`
Router prefix: `/v1`
Interactive docs: `http://localhost:8000/docs`

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/v1/health` | Service health check |
| GET | `/v1/templates` | List registered template IDs |
| GET | `/v1/playbooks` | List available playbook IDs |
| POST | `/v1/generate` | Run the generation pipeline |
| GET | `/v1/files/download` | Download a generated `.pptx` file |

Every response includes a `request_id` (UUID4 string) for tracing.

---

## POST /v1/generate

### Request body

```json
{
  "text":         "Raw input text to process.",
  "mode":         "deterministic",
  "template_id":  null,
  "preview_only": false,
  "artifacts":    false
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | required | Raw input text for the pipeline |
| `mode` | string | `"deterministic"` | `"deterministic"` or `"ai"` |
| `template_id` | string \| null | `null` | Override the template. Must be a registered ID. |
| `preview_only` | boolean | `false` | Plan slides without rendering a `.pptx` |
| `artifacts` | boolean | `false` | Export `spec.json`, `slide_plan.json`, `deck_definition.json` |

### Response body (200)

```json
{
  "request_id":    "550e8400-e29b-41d4-a716-446655440000",
  "success":       true,
  "playbook_id":   "meeting-notes-to-eos-rocks",
  "template_id":   "ops_review_v1",
  "mode":          "deterministic",
  "stage":         "rendered",
  "slide_count":   4,
  "slide_types":   ["title", "bullets", "bullets", "closing"],
  "output_path":   "/tmp/pptgen_api/abc123/output.pptx",
  "artifact_paths": null,
  "notes":         null
}
```

| Field | Description |
|---|---|
| `stage` | `"rendered"` (full generation) or `"deck_planned"` (preview only) |
| `output_path` | Absolute path to the `.pptx` file. `null` when `preview_only=true`. |
| `artifact_paths` | Map of artifact name → path. `null` unless `artifacts=true`. |
| `notes` | Optional diagnostic string from the pipeline. |

### Preview mode

When `preview_only=true`:
- `stage` is `"deck_planned"`
- `output_path` is `null`
- `slide_count` and `slide_types` are populated (the plan was built)
- No `.pptx` file is written

---

## Error Response Shape

All errors return HTTP 4xx with this body:

```json
{
  "detail": {
    "error":      "Human-readable error message.",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

The `request_id` in the error body matches the one that would have been returned
on success — use it to correlate errors with logs.

Common status codes:

| Code | Cause |
|---|---|
| 400 | Pipeline error (unknown mode, template not found, etc.) |
| 422 | Validation error (missing required field, wrong type) |

---

## GET /v1/files/download

Downloads a previously generated file by absolute path.

```
GET /v1/files/download?path=/tmp/pptgen_api/abc123/output.pptx
```

Returns the file as an attachment with content type
`application/vnd.openxmlformats-officedocument.presentationml.presentation`.

**Security constraint:** The `path` parameter must resolve to a file inside
`$TMPDIR/pptgen_api/`. Any path outside this subtree returns HTTP 403.
This prevents directory traversal attacks.

| Code | Cause |
|---|---|
| 200 | File returned as attachment |
| 403 | Path is outside the allowed subtree |
| 404 | File does not exist |

---

## request_id

Every request — success and error — produces a `request_id` (UUID4).

Use it to:
- Correlate API calls with server logs
- Report specific failures to the platform team
- Track which request produced a given `.pptx`

The Web UI displays the `request_id` on every result and provides a copy button.

---

## Running the Server

```bash
uvicorn pptgen.api.server:app --reload          # Development (auto-reload)
uvicorn pptgen.api.server:app --host 0.0.0.0    # Expose on all interfaces
```

Default port: `8000`

---

## CORS

The server allows cross-origin requests from the Vite dev server:

- `http://localhost:5173`
- `http://localhost:5174`
- `http://127.0.0.1:5173`

To add additional origins, edit `allow_origins` in `src/pptgen/api/server.py`.

---

## Environment / Configuration

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `web/.env` | Points the Web UI at a non-local API server. Empty string (default) uses the Vite proxy to `localhost:8000`. |

Example:
```bash
# web/.env
VITE_API_BASE_URL=http://api.internal.example.com
```
