# Observability & Operator Tooling

Stage 6D adds run telemetry persistence, structured JSON logging, operator inspection
APIs, and CLI commands for run history. No new infrastructure dependencies are required.

---

## Stage Timings Flow

Pipeline stage timings originate in `RunContext` and flow through to the SQLite run registry:

```
RunContext.timings          # list of StageTimer, populated during generate_presentation()
  └── ctx.as_dict()["timings"]
        └── ArtifactPromoter.promote(run_context_dict=ctx.as_dict())
              └── SQLiteRunStore.update_status(stage_timings=timings)
                    └── runs.stage_timings column (JSON text)
```

`RunRecord.stage_timings` is a list of dicts: `[{"stage": str, "duration_ms": float|None}]`.

`RunRecord.artifact_count` is the number of promoted artifacts (excluding the manifest).

### Schema Migration

`SQLiteRunStore._migrate_schema()` is called on every store open. It uses `PRAGMA table_info(runs)` to detect missing columns and issues `ALTER TABLE ADD COLUMN` only for absent ones. This is safe on both fresh and pre-existing `artifacts.db` files.

---

## Structured Logging

### Components

| File | Purpose |
|---|---|
| `src/pptgen/observability/__init__.py` | Package — exports `StructuredLogger`, `get_logger` |
| `src/pptgen/observability/structured_logger.py` | `JsonFormatter`, `StructuredLogger` |

### JsonFormatter

`JsonFormatter(logging.Formatter)` emits one JSON object per line:

```json
{
  "ts": 1711234567.123,
  "level": "INFO",
  "logger": "pptgen.artifacts.promoter",
  "message": "run_completed",
  "event": "run_completed",
  "run_id": "abc123def456...",
  "metadata": {"total_ms": 1234.5}
}
```

### Configuration

| Env Var | Settings Field | Default | Effect |
|---|---|---|---|
| `PPTGEN_LOG_LEVEL` | `log_level` | `INFO` | Root logger level |
| `PPTGEN_LOG_JSON_FORMAT` | `log_json_format` | `false` | Enable JSON log lines |

Set `PPTGEN_LOG_JSON_FORMAT=true` to switch to machine-readable JSON output.

### Log Event Catalog

| Event | Emitted by | Key Fields |
|---|---|---|
| `run_completed` | `ArtifactPromoter` | `run_id`, `total_ms` |
| `run_failed` | `ArtifactPromoter` | `run_id`, `error_category` |
| `job_claimed` | `JobWorker._execute()` | `job_id`, `run_id`, `worker_id` |
| `job_completed` | `JobWorker._execute()` | `job_id`, `run_id` |
| `job_failed` | `JobWorker._handle_failure()` | `job_id`, `run_id`, `error` |
| `artifact_promoted` | `ArtifactPromoter` | `run_id`, `artifact_type`, `size_bytes`, `checksum` |

---

## Operator APIs

### GET /v1/runs

List runs with optional filters and pagination.

**Query params:** `limit` (default 50), `offset` (default 0), `status`, `source`

**Response:**
```json
{
  "runs": [
    {
      "run_id": "abc123...",
      "status": "succeeded",
      "source": "api_async",
      "job_id": "job456...",
      "started_at": "2026-03-24T10:00:00+00:00",
      "completed_at": "2026-03-24T10:00:02.345+00:00",
      "total_ms": 2345.1,
      "artifact_count": 4,
      "error_category": null
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### GET /v1/runs/{run_id}/metrics

Per-run timing breakdown.

**Response:**
```json
{
  "run_id": "abc123...",
  "total_ms": 2345.1,
  "artifact_count": 4,
  "stage_timings": [
    {"stage": "spec_generation", "duration_ms": 312.0},
    {"stage": "slide_planning", "duration_ms": 98.5},
    {"stage": "deck_build", "duration_ms": 45.0},
    {"stage": "render", "duration_ms": 1889.6}
  ],
  "slowest_stage": "render",
  "fastest_stage": "deck_build"
}
```

### GET /v1/jobs/{job_id}/runs

All run records linked to an async job (typically one, but may be multiple on retry).

**Response:** `list[RunListItemResponse]` — same shape as items in `/v1/runs`.

---

## CLI Commands

CLI commands read directly from SQLite via `SQLiteRunStore.from_settings()`. They do not
make HTTP calls. Ensure `PPTGEN_ARTIFACT_DB_PATH` (or the default workspace path) points
to the correct database.

### pptgen runs list

```
pptgen runs list [--limit N] [--offset N] [--status STATUS] [--source SOURCE] [--json]
```

```
RUN_ID                             STATUS       SOURCE           MS  STARTED
abc123def456789012345678901234ab   succeeded    api_async      1234  2026-03-24T10:00:00
def456789012345678901234ab012345   failed       api_sync          -  2026-03-24T09:55:00
```

### pptgen runs show <run_id>

```
Run ID:        abc123def456789012345678901234ab
Status:        succeeded
Source:        api_async
Job ID:        job456789...
Playbook:      engineering_delivery
Template:      ops_review_v1
Started:       2026-03-24T10:00:00+00:00
Completed:     2026-03-24T10:00:02+00:00
Total ms:      2345.0
Artifact cnt:  4
```

### pptgen runs metrics <run_id>

```
Run: abc123...  total=2345.0 ms  artifacts=4

  STAGE                               MS
  spec_generation                  312.0
  slide_planning                    98.5
  deck_build                        45.0
  render                          1889.6
```

All commands accept `--json` for machine-readable output.

---

## Source Files

| File | Purpose |
|---|---|
| `src/pptgen/observability/__init__.py` | Package exports |
| `src/pptgen/observability/structured_logger.py` | `JsonFormatter`, `StructuredLogger`, `get_logger` |
| `src/pptgen/runs/models.py` | `RunRecord.stage_timings`, `RunRecord.artifact_count` |
| `src/pptgen/runs/sqlite_store.py` | `_migrate_schema()`, extended `update_status()`, `list_runs()`, `list_for_job()` |
| `src/pptgen/artifacts/promoter.py` | Passes timings/count to `update_status()`, emits log events |
| `src/pptgen/api/run_routes.py` | `GET /v1/runs`, `GET /v1/runs/{run_id}/metrics` |
| `src/pptgen/api/job_routes.py` | `GET /v1/jobs/{job_id}/runs` |
| `src/pptgen/api/schemas.py` | `RunListItemResponse`, `RunListResponse`, `RunMetricsResponse` |
| `src/pptgen/cli/run_commands.py` | `pptgen runs list/show/metrics` |
