# Configuration Reference

All pptgen runtime behaviour is controlled by `RuntimeSettings` — a frozen
dataclass loaded once per process from environment variables.  No configuration
files are required; defaults are suitable for local development.

---

## Environment Variable Reference

| Environment Variable | Field | Type | Default | Description |
|---|---|---|---|---|
| `PPTGEN_PROFILE` | `profile` | `dev`/`test`/`prod` | `dev` | Runtime profile — selects profile-specific defaults |
| `PPTGEN_WORKSPACE_BASE` | `workspace_base` | path string | `""` | Base dir for workspace dirs; empty → `$TMPDIR/pptgen_api` |
| `PPTGEN_WORKSPACE_TTL_HOURS` | `workspace_ttl_hours` | int | `24` | Hours before workspace directories are eligible for cleanup |
| `PPTGEN_MAX_INPUT_BYTES` | `max_input_bytes` | int | `524288` | Maximum raw input size in bytes (enforced in pipeline) |
| `PPTGEN_MAX_ARTIFACT_BYTES` | `max_artifact_bytes` | int | `104857600` | Maximum artifact file size in bytes |
| `PPTGEN_PIPELINE_TIMEOUT` | `pipeline_timeout_seconds` | int | `120` | Pipeline stage timeout in seconds (enforcement in Stage 6B) |
| `PPTGEN_RENDER_TIMEOUT` | `render_timeout_seconds` | int | `60` | Render stage timeout in seconds (enforcement in Stage 6B) |
| `PPTGEN_AI_TIMEOUT` | `ai_model_timeout_seconds` | int | `30` | AI model call timeout in seconds (enforcement in Stage 6B) |
| `PPTGEN_ENABLE_AI_MODE` | `enable_ai_mode` | bool | `true` | Enable `ai` execution mode |
| `PPTGEN_ENABLE_ARTIFACT_EXPORT` | `enable_artifact_export` | bool | `true` | Enable pipeline artifact export |
| `PPTGEN_MODEL_PROVIDER` | `model_provider` | string | `mock` | LLM provider: `mock`, `anthropic`, `openai`, `ollama` |
| `PPTGEN_MODEL_NAME` | `model_name` | string | `""` | Provider-specific model identifier; empty = provider default |
| `PPTGEN_MODEL_API_KEY` | `model_api_key` | string | `""` | LLM API key — **never hardcode** |
| `PPTGEN_API_HOST` | `api_host` | string | `0.0.0.0` | uvicorn bind host |
| `PPTGEN_API_PORT` | `api_port` | int | `8000` | uvicorn bind port |
| `PPTGEN_CORS_ORIGINS` | `api_cors_origins` | comma-separated | `localhost:5173,5174` | Allowed CORS origins |

---

## Profile-Specific Defaults

Profile defaults apply when the corresponding environment variable is **not set**.
When an env var is set, it always takes precedence over the profile default.

| Field | `dev` | `test` | `prod` |
|---|---|---|---|
| `max_input_bytes` | 524 288 (512 KB) | 131 072 (128 KB) | 1 048 576 (1 MB) |
| `pipeline_timeout_seconds` | 300 | 30 | 120 |

Select a profile:

```bash
export PPTGEN_PROFILE=prod
```

---

## Config Fingerprint

`RuntimeSettings.fingerprint` returns an 8-character SHA-256 hex digest of all
non-secret settings fields (excluding `model_api_key`).  It is stored in
`RunContext.config_fingerprint` for every pipeline run, enabling reproducibility
debugging: the same fingerprint means the same configuration was active.

---

## Singleton Pattern

Settings are loaded once per process on the first call to `get_settings()` and
cached for the process lifetime.

```python
from pptgen.config import get_settings

settings = get_settings()
print(settings.max_input_bytes)   # 524288 (default dev)
```

**Test isolation** — the singleton must be reset between tests to avoid
cross-test pollution.  The `conftest.py` `reset_settings` autouse fixture
handles this automatically.  To override manually:

```python
from pptgen.config import RuntimeSettings, override_settings

override_settings(RuntimeSettings(max_input_bytes=1000))
# … test code …
override_settings(None)   # always reset
```

---

## Usage Examples

### Local development (defaults)

```bash
pptgen generate notes/meeting.txt
```

No environment variables needed.  Profile `dev` is used automatically.

### Production API server

```bash
export PPTGEN_PROFILE=prod
export PPTGEN_MODEL_PROVIDER=anthropic
export PPTGEN_MODEL_API_KEY=sk-ant-...
export PPTGEN_WORKSPACE_BASE=/var/pptgen/workspaces
uvicorn pptgen.api.server:app --host 0.0.0.0 --port 8000
```

### Test suite

The `conftest.py` fixture sets `PPTGEN_PROFILE=test` via monkeypatch for
profile-sensitive tests.  Override specific fields directly:

```python
from pptgen.config import RuntimeSettings, override_settings

def test_something(monkeypatch):
    override_settings(RuntimeSettings(max_input_bytes=500))
    # … test code …
    override_settings(None)
```

---

## Implementation

- Source: [`src/pptgen/config/settings.py`](../../src/pptgen/config/settings.py)
- Public API: [`src/pptgen/config/__init__.py`](../../src/pptgen/config/__init__.py)
- Tests: [`tests/unit/test_settings.py`](../../tests/unit/test_settings.py)
