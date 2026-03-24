# Job Execution Model

Stage 6B adds a durable async job queue alongside the existing synchronous
`/v1/generate` endpoint. Long-running presentations can be submitted to a
background queue and polled for completion.

---

## Architecture

```
Client
  │
  ├─ POST /v1/generate   →  sync, returns .pptx URL immediately
  │
  └─ POST /v1/jobs       →  async, returns job_id (202 Accepted)
       │
       └─ SQLiteJobStore (jobs.db)
              │
              └─ JobWorker (daemon thread)
                    │
                    └─ generate_presentation()  →  WorkspaceManager
```

---

## Components

### JobRecord

Dataclass representing a single job. Key fields:

| Field | Type | Description |
|---|---|---|
| `job_id` | str | 32-hex unique identifier |
| `run_id` | str | Pipeline run ID (workspace directory name) |
| `status` | `JobStatus` | Current state |
| `workload_type` | `WorkloadType` | `interactive` (priority 10) or `batch` (priority 0) |
| `retry_count` | int | Number of execution attempts so far |
| `max_retries` | int | Maximum attempts before terminal failure |
| `error_category` | str | `ErrorCategory` value if failed |
| `output_path` | str | Path to rendered `.pptx`, if succeeded |

### JobStatus

```
queued → running → succeeded
                 → failed
                 → retrying → running (again)
queued → cancelled
running → timed_out  (reserved for Stage 6C)
```

### SQLiteJobStore

Thread-safe SQLite store using WAL mode and `threading.Lock` for write
serialization. File location:

- Default: `{PPTGEN_WORKSPACE_BASE}/jobs.db`
- Override: `PPTGEN_JOB_DB_PATH`

### JobWorker

Single daemon thread started in the FastAPI lifespan hook. Poll loop:

1. Call `claim_next(worker_id)` — atomic conditional UPDATE
2. Execute `generate_presentation()` in the calling thread
3. On success: `update_status(SUCCEEDED, output_path=...)`
4. On failure: apply retry policy → `RETRYING` or `FAILED`
5. Wait `PPTGEN_WORKER_POLL_INTERVAL` seconds if queue is empty

**Crash recovery:** On startup, any jobs in `running` state older than
`PPTGEN_WORKER_STALE_TIMEOUT_MINUTES` are reset to `retrying` (or `failed`
if max retries exceeded).

---

## Retry Policy

| Error category | Retryable? |
|---|---|
| `ai_provider` | Yes — transient LLM failure |
| `system` | Yes — unexpected error |
| `validation` | No — bad input won't improve |
| `configuration` | No — misconfiguration requires operator fix |
| `rendering` | No — template issue won't self-heal |
| `connector` | No — source file issue |

Backoff: `min(2^retry_count, 60)` seconds.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/jobs` | Submit job, returns 202 with `JobStatusResponse` |
| `GET` | `/v1/jobs/{job_id}` | Poll job status |
| `POST` | `/v1/jobs/{job_id}/cancel` | Cancel queued/retrying job |

### Submit request

```json
{
  "input_text": "Meeting notes. Attendees: Alice...",
  "template_id": "ops_review_v1",
  "mode": "deterministic",
  "workload_type": "interactive",
  "artifacts": false
}
```

### Status response

```json
{
  "job_id": "abc123...",
  "run_id": "def456...",
  "status": "succeeded",
  "workload_type": "interactive",
  "submitted_at": "2026-03-23T10:00:00+00:00",
  "started_at": "2026-03-23T10:00:01+00:00",
  "completed_at": "2026-03-23T10:00:03+00:00",
  "retry_count": 0,
  "output_path": "/tmp/pptgen_api/def456.../output.pptx"
}
```

---

## CLI Commands

```bash
# Submit a job
pptgen job submit notes/meeting.txt

# Submit as batch priority
pptgen job submit notes/meeting.txt --batch

# Check status
pptgen job status <job_id>

# Check status as JSON
pptgen job status <job_id> --json
```

---

## Configuration

| Environment Variable | Field | Default | Description |
|---|---|---|---|
| `PPTGEN_JOB_DB_PATH` | `job_db_path` | `{workspace_base}/jobs.db` | SQLite DB file path |
| `PPTGEN_WORKER_POLL_INTERVAL` | `worker_poll_interval_seconds` | `2.0` | Seconds between polls |
| `PPTGEN_MAX_JOB_RETRIES` | `max_job_retries` | `3` | Max retries per job |
| `PPTGEN_WORKER_STALE_TIMEOUT_MINUTES` | `worker_stale_job_timeout_minutes` | `15` | Stale job timeout |

---

## Source Files

| File | Purpose |
|---|---|
| `src/pptgen/jobs/models.py` | `JobRecord`, `JobStatus`, `WorkloadType` |
| `src/pptgen/jobs/store.py` | `AbstractJobStore` Protocol |
| `src/pptgen/jobs/sqlite_store.py` | `SQLiteJobStore` implementation |
| `src/pptgen/jobs/retry.py` | `is_retryable()`, `get_backoff_seconds()` |
| `src/pptgen/jobs/worker.py` | `JobWorker` daemon thread |
| `src/pptgen/api/job_routes.py` | REST endpoints |
| `src/pptgen/cli/job_commands.py` | CLI commands |
