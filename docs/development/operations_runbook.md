# Operations Runbook

Operator reference for running and maintaining the pptgen platform.

---

## Startup Validation

Every API server start and every CLI command runs startup validation before
processing requests.  The checks are:

| Check | Failure message |
|---|---|
| Template registry exists and is readable | `Template registry not found: <path>` |
| Workspace base directory is writable | `Workspace base not writable: <path>` |
| AI provider API key present (when non-mock) | `PPTGEN_MODEL_API_KEY required when model_provider='...'` |
| `max_input_bytes` is positive | `max_input_bytes must be a positive integer` |

**API server**: validation is fatal — the server refuses to start if any check
fails.

**CLI**: validation is non-fatal — warnings are printed to stderr and the command
continues.  This allows offline/airgapped usage.

To run validation manually:

```python
from pptgen.config import get_settings
from pptgen.runtime.startup import validate_startup

failures = validate_startup(get_settings())
for f in failures:
    print(f"FAIL: {f}")
```

---

## Workspace Management

Each pipeline run writes to an isolated workspace directory under
`$PPTGEN_WORKSPACE_BASE/<run_id>/` (default: `$TMPDIR/pptgen_api/<run_id>/`).

### Directory layout

```
$WORKSPACE_BASE/
  <run_id>/
    output.pptx        ← rendered presentation
    artifacts/         ← spec.json, slide_plan.json, deck_definition.json
```

### Workspace cleanup

Workspaces are not automatically deleted after a run (they persist for file
download).  Clean up manually:

```python
from pptgen.config import get_settings
from pptgen.runtime.workspace import WorkspaceManager

mgr = WorkspaceManager.from_settings(get_settings())

# Delete workspaces older than 24 hours
deleted = mgr.cleanup_older_than(hours=24)
print(f"Deleted {deleted} workspace(s)")

# Delete a specific workspace
mgr.cleanup("abc123def456...")
```

Automated TTL cleanup (scheduled task / background thread) will be added in Stage 6B.

---

## Environment Setup

### Local development

```bash
# No environment variables required — defaults work out of the box.
cd pptgen
pip install -e ".[dev]"
pptgen generate notes/meeting.txt
```

### API server (production)

```bash
export PPTGEN_PROFILE=prod
export PPTGEN_MODEL_PROVIDER=anthropic        # or openai, ollama
export PPTGEN_MODEL_API_KEY=sk-ant-...        # never commit
export PPTGEN_WORKSPACE_BASE=/var/pptgen/ws   # persistent volume
export PPTGEN_WORKSPACE_TTL_HOURS=48          # keep files 48 h

uvicorn pptgen.api.server:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2
```

### Docker (example)

```dockerfile
ENV PPTGEN_PROFILE=prod
ENV PPTGEN_WORKSPACE_BASE=/tmp/pptgen_api
ENV PPTGEN_MODEL_PROVIDER=mock
# PPTGEN_MODEL_API_KEY — inject at runtime, never build into image
```

---

## Log Patterns

The platform emits structured data through `RunContext.as_dict()`.  Key fields
to monitor:

| Field | Meaning |
|---|---|
| `run_id` | Unique 32-hex-char run identifier |
| `request_id` | HTTP request ID (API only) |
| `profile` | Active runtime profile |
| `config_fingerprint` | 8-char settings hash for reproducibility |
| `timings[*].stage` | Stage name (`route_input`, `execute_playbook`, `plan_slides`, `convert_spec`, `render`) |
| `timings[*].duration_ms` | Stage duration in milliseconds |
| `total_ms` | Wall-clock span of the full pipeline execution |

To emit run metadata in a CLI script:

```python
import json
from pptgen.runtime import RunContext
from pptgen.pipeline import generate_presentation

ctx = RunContext()
result = generate_presentation(text, run_context=ctx)
print(json.dumps(ctx.as_dict(), indent=2))
```

---

## Common Failure Scenarios

### Template registry not found

**Symptom**: `Template registry not found: …/templates/registry.yaml`

**Cause**: Running from the wrong working directory, or the repo is incomplete.

**Fix**: Ensure you are running from the repository root where `templates/` exists.

---

### Workspace not writable

**Symptom**: `Workspace base not writable: /var/pptgen/ws`

**Cause**: The workspace base path does not exist or the process lacks write
permission.

**Fix**: Create the directory and set correct permissions:

```bash
mkdir -p /var/pptgen/ws
chmod 755 /var/pptgen/ws
```

---

### Input size rejected

**Symptom**: `InputSizeError: Input exceeds maximum size of N bytes`

**Cause**: The submitted text exceeds `PPTGEN_MAX_INPUT_BYTES`.

**Fix for operators**: Increase the limit via environment variable:

```bash
export PPTGEN_MAX_INPUT_BYTES=2097152   # 2 MB
```

**Fix for users**: Split large documents and submit separately.

---

### AI provider API key missing

**Symptom**: `PPTGEN_MODEL_API_KEY required when model_provider='anthropic'`

**Cause**: `PPTGEN_MODEL_PROVIDER` is set to a non-mock provider but no API
key is configured.

**Fix**: Set the key in the environment (never in code):

```bash
export PPTGEN_MODEL_API_KEY=sk-ant-...
```

---

## Testing the Configuration

```bash
# Run configuration tests
pytest tests/unit/test_settings.py -v

# Run all Stage 6A runtime tests
pytest tests/unit/test_settings.py \
       tests/unit/test_run_context.py \
       tests/unit/test_workspace.py \
       tests/unit/test_startup.py \
       tests/unit/test_errors.py \
       tests/unit/test_generation_pipeline_stage6a.py \
       -v
```
