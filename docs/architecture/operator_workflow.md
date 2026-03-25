# Operator Workflow — Run Dashboard & Observability

This document describes how operators and developers use the pptgen web UI and API to inspect, debug, and manage presentation generation runs.

---

## Overview

The operator dashboard is a React SPA served alongside the FastAPI backend. It provides:

- A **Runs list** (`/runs`) — paginated table of recent runs with status, playbook, duration, and artifact counts
- A **Run detail view** (`/runs/:runId`) — full run metadata, stage timings, artifact list, and manifest viewer
- A **Generate page** (`/`) — interactive form for submitting and previewing sync generation requests

---

## Runs List Page

The Runs page calls `GET /v1/runs` on mount and on each Refresh click. The response shape is:

```json
{
  "runs": [...],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

Each run item includes `run_id`, `status`, `playbook_id`, `mode`, `started_at`, `total_ms`, and `artifact_count`.

**Duration display rules:**

1. If `total_ms > 0` → use it directly
2. If `status === 'running'` → compute `Date.now() - started_at` (live elapsed)
3. If `completed_at` is set → compute `completed_at - started_at` as fallback (handles runs where `total_ms` was not persisted)
4. Otherwise → show `—`

**Visual conventions:**

- Failed rows have a red left border (`run-table__row--failed`)
- Run IDs are truncated to 8 characters; hover the cell for the full ID via the `title` attribute

---

## Run Detail Page

Navigating to `/runs/:runId` fires three parallel fetches in hook-declaration order:

1. `GET /v1/runs/:runId` → run metadata
2. `GET /v1/runs/:runId/metrics` → stage timings (non-fatal — page renders even if this 404s)
3. `GET /v1/runs/:runId/artifacts` → artifact list

**Stage Timings card:**

- Shows a table of `{stage, duration_ms}` pairs
- Highlights the slowest stage row with a warm yellow background (`run-metrics-card__row--slowest`)
- Slowest/fastest stage names appear in the annotation line below the table

**Artifact list:**

- Sorted by category: final output → manifest → internal artifacts
- Within category, sorted by `created_at DESC` (backend timestamp)
- Final output items have a blue left border; manifest items have grey; internal have light grey
- Download links are only shown for `status==='present' && visibility==='downloadable'` artifacts
- Category icons: 📊 final, 📋 manifest, 📄 internal

**Manifest viewer:**

- Collapsed by default; expands on first click
- Fetches `GET /v1/runs/:runId/manifest` lazily (only on first expand)
- Cached — collapse/re-expand does not re-fetch

**Download CTA:**

When the run has a final-output artifact (`is_final_output=true, status='present'`), a prominent "Download Presentation" link appears in the page header. If multiple final-output artifacts exist, the most recent by `created_at` is used.

---

## Data Quality Notes

### Stage timings and `total_ms`

Stage timings are recorded by `RunContext` during pipeline execution. The context must be passed explicitly:

```python
# service.py — sync API path
result = generate_presentation(
    text,
    ...,
    run_context=ctx,   # required for timings to be recorded
)
```

Without `run_context=ctx`, `ctx.total_ms()` returns `0.0` and `ctx.playbook_id` remains `None`. The async worker path already passes `run_context` correctly.

### Timing persistence

After promotion, stage timings are serialized as JSON and stored in the `runs.stage_timings` column. The metrics API endpoint (`GET /v1/runs/:runId/metrics`) reads this column and computes `slowest_stage` / `fastest_stage` on the fly.

---

## API Reference

| Endpoint | Description |
|---|---|
| `GET /v1/runs` | List runs. Params: `limit`, `offset`, `status`, `source`, `mode` |
| `GET /v1/runs/:runId` | Full run record |
| `GET /v1/runs/:runId/metrics` | Stage timings + artifact count |
| `GET /v1/runs/:runId/artifacts` | Artifact metadata list |
| `GET /v1/runs/:runId/manifest` | Run manifest JSON |
| `GET /v1/jobs/:jobId/runs` | Runs associated with an async job |

---

## CLI Commands

Direct SQLite inspection (no HTTP server required):

```bash
# List recent runs
pptgen runs list
pptgen runs list --status failed
pptgen runs list --json

# Show full run details
pptgen runs show <run_id>
pptgen runs show <run_id> --json

# Show stage timings
pptgen runs metrics <run_id>
pptgen runs metrics <run_id> --json
```

Requires `PPTGEN_ARTIFACT_DB_PATH` to point to the SQLite database (or the default path from settings).
