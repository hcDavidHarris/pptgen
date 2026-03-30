"""Typed runtime configuration for pptgen.

Settings are loaded once per process from environment variables with the
``PPTGEN_`` prefix.  A module-level singleton is returned by
:func:`get_settings` and is safe to call from any module.

Environment variable reference
-------------------------------

====================== ================================= ==========
Variable               Description                       Default
====================== ================================= ==========
PPTGEN_PROFILE         Runtime profile (dev/test/prod)   dev
PPTGEN_WORKSPACE_BASE  Override workspace base path      (tempdir)
PPTGEN_WORKSPACE_TTL_HOURS  Hours before workspace cleanup  24
PPTGEN_MAX_INPUT_BYTES Maximum raw-text input size        524288
PPTGEN_MAX_ARTIFACT_BYTES   Maximum artifact file size   104857600
PPTGEN_PIPELINE_TIMEOUT Pipeline stage timeout (s)       120
PPTGEN_RENDER_TIMEOUT  Render stage timeout (s)           60
PPTGEN_AI_TIMEOUT      AI model call timeout (s)          30
PPTGEN_ENABLE_AI_MODE  Enable ai execution mode           true
PPTGEN_ENABLE_ARTIFACT_EXPORT  Enable artifact export    true
PPTGEN_MODEL_PROVIDER  LLM provider (mock/anthropic/…)   mock
PPTGEN_MODEL_NAME      Provider-specific model name       (provider default)
PPTGEN_MODEL_API_KEY   API key — never hardcode           (empty)
PPTGEN_OLLAMA_TIMEOUT  Ollama HTTP request timeout (s)    120
PPTGEN_API_HOST        uvicorn bind host                  0.0.0.0
PPTGEN_API_PORT        uvicorn bind port                  8000
PPTGEN_CORS_ORIGINS    Comma-separated CORS origins       localhost:5173,5174
====================== ================================= ==========

Usage::

    from pptgen.config import get_settings

    settings = get_settings()
    print(settings.max_input_bytes)   # 524288

Test isolation::

    from pptgen.config import override_settings, RuntimeSettings
    override_settings(RuntimeSettings(max_input_bytes=1000))
    # … test code …
    override_settings(None)  # reset to env-derived defaults
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Profile(str, Enum):
    """Runtime environment profile.

    Select via the ``PPTGEN_PROFILE`` environment variable.
    """

    DEV = "dev"
    TEST = "test"
    PROD = "prod"


# Per-profile defaults that differ from the global defaults.
# Missing keys fall back to the field defaults on RuntimeSettings.
_PROFILE_DEFAULTS: dict[str, dict[str, int]] = {
    "dev": {
        "max_input_bytes": 524_288,        # 512 KB
        "pipeline_timeout_seconds": 300,
    },
    "test": {
        "max_input_bytes": 131_072,        # 128 KB
        "pipeline_timeout_seconds": 30,
    },
    "prod": {
        "max_input_bytes": 1_048_576,      # 1 MB
        "pipeline_timeout_seconds": 120,
    },
}


@dataclass(frozen=True)
class RuntimeSettings:
    """Immutable typed settings for the pptgen platform.

    All fields have defaults suitable for local development.  Use
    :meth:`from_env` to load from environment variables, or construct
    directly in tests.
    """

    # ------------------------------------------------------------------
    # Environment
    # ------------------------------------------------------------------
    profile: Profile = Profile.DEV

    # ------------------------------------------------------------------
    # Workspace
    # ------------------------------------------------------------------
    #: Base directory for per-run workspace directories.  Empty string
    #: causes :attr:`workspace_base_path` to use the system temp dir.
    workspace_base: str = ""
    workspace_ttl_hours: int = 24

    # ------------------------------------------------------------------
    # Input / output size limits
    # ------------------------------------------------------------------
    max_input_bytes: int = 524_288          # 512 KB
    max_artifact_bytes: int = 104_857_600   # 100 MB

    # ------------------------------------------------------------------
    # Timeouts (seconds)
    # Enforcement for sync pipeline stages is deferred to Stage 6B.
    # These values are exposed in RunContext for observability.
    # ------------------------------------------------------------------
    pipeline_timeout_seconds: int = 120
    render_timeout_seconds: int = 60
    ai_model_timeout_seconds: int = 30

    # ------------------------------------------------------------------
    # Feature flags
    # ------------------------------------------------------------------
    enable_ai_mode: bool = True
    enable_artifact_export: bool = True

    # ------------------------------------------------------------------
    # Model / provider
    # ------------------------------------------------------------------
    #: Provider name.  Valid values: ``"mock"``, ``"anthropic"``,
    #: ``"openai"``, ``"ollama"``.
    model_provider: str = "mock"
    #: Provider-specific model identifier.  Empty string = use the
    #: provider's own default (e.g. ``claude-sonnet-4-6`` for Anthropic).
    model_name: str = ""
    #: API key — injected from PPTGEN_MODEL_API_KEY.  Never hardcode.
    model_api_key: str = ""

    # ------------------------------------------------------------------
    # Ollama provider settings (model_provider = "ollama")
    # ------------------------------------------------------------------
    #: Ollama model tag to use.  Override via PPTGEN_OLLAMA_MODEL.
    ollama_model: str = "qwen3:latest"
    #: Base URL of the running Ollama instance.
    #: Override via PPTGEN_OLLAMA_BASE_URL (e.g. http://remote-host:11434).
    ollama_base_url: str = "http://localhost:11434"
    #: HTTP request timeout for Ollama calls in seconds.
    #: Local model inference can be slow; 120 s is a safe default.
    #: Override via PPTGEN_OLLAMA_TIMEOUT.
    ollama_timeout_seconds: int = 120

    # ------------------------------------------------------------------
    # API server
    # ------------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    #: Comma-separated allowed CORS origins stored as an immutable tuple.
    api_cors_origins: tuple[str, ...] = field(
        default_factory=lambda: ("http://localhost:5173", "http://localhost:5174")
    )

    # ------------------------------------------------------------------
    # Job execution (Stage 6B)
    # ------------------------------------------------------------------
    #: Path to the SQLite job database file.  Empty string defaults to
    #: ``{workspace_base_path}/jobs.db``.
    job_db_path: str = ""
    #: Seconds between worker poll cycles.
    worker_poll_interval_seconds: float = 2.0
    #: Maximum number of job retries before terminal failure.
    max_job_retries: int = 3
    #: Minutes a job may stay in 'running' state before being considered stale.
    worker_stale_job_timeout_minutes: int = 15

    # ------------------------------------------------------------------
    # Artifact and Run Registry (Stage 6C)
    # ------------------------------------------------------------------
    #: SQLite DB for run/artifact registry. Empty = {workspace_base}/artifacts.db
    artifact_db_path: str = ""
    #: Durable artifact filesystem root. Empty = {workspace_base}/artifact_store
    artifact_store_base: str = ""
    #: Retention hours for "longest" class (pptx). Default 7 days.
    artifact_retention_longest_hours: int = 168
    #: Retention hours for "medium" class (spec/plan/deck_def). Default 3 days.
    artifact_retention_medium_hours: int = 72
    #: Retention hours for "shorter" class (logs/diagnostics). Default 1 day.
    artifact_retention_shorter_hours: int = 24

    # ------------------------------------------------------------------
    # Observability (Stage 6D)
    # ------------------------------------------------------------------
    #: Log level for the root logger. Default INFO.
    log_level: str = "INFO"
    #: Emit structured JSON log lines when True.
    log_json_format: bool = False

    # ------------------------------------------------------------------
    # Design System (Phase 9 Stage 1 / Phase 10B)
    # ------------------------------------------------------------------
    #: Path to the design_system/ directory.  Empty string = use the
    #: ``design_system/`` directory adjacent to the project source root.
    design_system_path: str = ""
    #: Platform-level default theme ID.  Applied when no theme is
    #: specified at run-time or in the template.  Empty string = no theme.
    default_theme: str = ""
    #: When True, DRAFT-status artifacts are allowed through the pipeline
    #: without raising GovernanceViolationError.  Defaults to False so that
    #: unreviewed artifacts cannot reach production.
    allow_draft_artifacts: bool = False

    # ------------------------------------------------------------------
    # Governance Analytics (Phase 10D)
    # ------------------------------------------------------------------
    #: Directory for append-only analytics files (run_records.jsonl,
    #: usage_events.jsonl, usage_aggregates.json).
    #: Empty string = analytics disabled (no files written).
    #: Set PPTGEN_ANALYTICS_DIR to enable, e.g. ~/.pptgen/analytics.
    analytics_dir: str = ""

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def job_db_file(self) -> Path:
        """Absolute path to the SQLite job database file."""
        if self.job_db_path:
            return Path(self.job_db_path)
        return self.workspace_base_path / "jobs.db"

    @property
    def artifact_db_file(self) -> Path:
        """Absolute path to the SQLite artifact/run registry database."""
        if self.artifact_db_path:
            return Path(self.artifact_db_path)
        return self.workspace_base_path / "artifacts.db"

    @property
    def artifact_store_path(self) -> Path:
        """Absolute path to the durable artifact filesystem root."""
        if self.artifact_store_base:
            return Path(self.artifact_store_base)
        return self.workspace_base_path / "artifact_store"

    @property
    def workspace_base_path(self) -> Path:
        """Absolute path to the workspace root directory.

        Returns the configured override, or ``$TMPDIR/pptgen_api`` when
        :attr:`workspace_base` is empty.
        """
        base = self.workspace_base or str(Path(tempfile.gettempdir()) / "pptgen_api")
        return Path(base)

    @property
    def analytics_dir_path(self) -> Path | None:
        """Absolute path to the analytics output directory, or ``None``.

        ``None`` when :attr:`analytics_dir` is empty, which disables all
        analytics writes.  Set ``PPTGEN_ANALYTICS_DIR`` to enable.
        """
        return Path(self.analytics_dir) if self.analytics_dir else None

    @property
    def design_system_root(self) -> Path:
        """Absolute path to the design_system/ directory.

        Returns the configured override, or the ``design_system/`` directory
        adjacent to the project source root (``src/pptgen/../../design_system``).
        """
        if self.design_system_path:
            return Path(self.design_system_path)
        # Default: design_system/ at the project root, relative to this file
        # (src/pptgen/config/settings.py → ../../../../design_system/)
        return Path(__file__).parent.parent.parent.parent / "design_system"

    @property
    def fingerprint(self) -> str:
        """8-character stable hash of non-secret settings.

        Suitable for storing in :class:`~pptgen.runtime.run_context.RunContext`
        to support reproducibility and debugging.  The ``model_api_key`` field
        is always excluded from the hash.
        """
        data = {
            k: v
            for k, v in self.__dict__.items()
            if k != "model_api_key"
        }
        serialized = json.dumps(data, sort_keys=True, default=str).encode()
        return hashlib.sha256(serialized).hexdigest()[:8]

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> RuntimeSettings:
        """Load :class:`RuntimeSettings` from environment variables.

        Environment variables take precedence over profile defaults, which
        take precedence over the field defaults on this class.
        """
        profile_str = os.environ.get("PPTGEN_PROFILE", Profile.DEV.value)
        try:
            profile = Profile(profile_str)
        except ValueError:
            profile = Profile.DEV

        pd = _PROFILE_DEFAULTS.get(profile.value, {})

        def _int(env_key: str, field_name: str, default: int) -> int:
            """Read int from env, falling back to profile default then hard default."""
            return int(os.environ.get(env_key, pd.get(field_name, default)))

        def _bool(key: str, default: bool) -> bool:
            return os.environ.get(key, str(default)).lower() not in {"false", "0", "no"}

        cors_raw = os.environ.get(
            "PPTGEN_CORS_ORIGINS",
            "http://localhost:5173,http://localhost:5174",
        )
        cors_origins = tuple(o.strip() for o in cors_raw.split(",") if o.strip())

        return cls(
            profile=profile,
            workspace_base=os.environ.get("PPTGEN_WORKSPACE_BASE", ""),
            workspace_ttl_hours=_int("PPTGEN_WORKSPACE_TTL_HOURS", "workspace_ttl_hours", 24),
            max_input_bytes=_int("PPTGEN_MAX_INPUT_BYTES", "max_input_bytes", 524_288),
            max_artifact_bytes=_int("PPTGEN_MAX_ARTIFACT_BYTES", "max_artifact_bytes", 104_857_600),
            pipeline_timeout_seconds=_int("PPTGEN_PIPELINE_TIMEOUT", "pipeline_timeout_seconds", 120),
            render_timeout_seconds=_int("PPTGEN_RENDER_TIMEOUT", "render_timeout_seconds", 60),
            ai_model_timeout_seconds=_int("PPTGEN_AI_TIMEOUT", "ai_model_timeout_seconds", 30),
            enable_ai_mode=_bool("PPTGEN_ENABLE_AI_MODE", True),
            enable_artifact_export=_bool("PPTGEN_ENABLE_ARTIFACT_EXPORT", True),
            model_provider=os.environ.get("PPTGEN_MODEL_PROVIDER", "mock"),
            model_name=os.environ.get("PPTGEN_MODEL_NAME", ""),
            model_api_key=os.environ.get("PPTGEN_MODEL_API_KEY", ""),
            ollama_model=os.environ.get("PPTGEN_OLLAMA_MODEL", "qwen3:latest"),
            ollama_base_url=os.environ.get("PPTGEN_OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_timeout_seconds=_int("PPTGEN_OLLAMA_TIMEOUT", "ollama_timeout_seconds", 120),
            api_host=os.environ.get("PPTGEN_API_HOST", "0.0.0.0"),
            api_port=_int("PPTGEN_API_PORT", "api_port", 8000),
            api_cors_origins=cors_origins,
            job_db_path=os.environ.get("PPTGEN_JOB_DB_PATH", ""),
            worker_poll_interval_seconds=float(
                os.environ.get("PPTGEN_WORKER_POLL_INTERVAL", "2.0")
            ),
            max_job_retries=_int("PPTGEN_MAX_JOB_RETRIES", "max_job_retries", 3),
            worker_stale_job_timeout_minutes=_int(
                "PPTGEN_WORKER_STALE_TIMEOUT_MINUTES",
                "worker_stale_job_timeout_minutes",
                15,
            ),
            artifact_db_path=os.environ.get("PPTGEN_ARTIFACT_DB_PATH", ""),
            artifact_store_base=os.environ.get("PPTGEN_ARTIFACT_STORE_BASE", ""),
            artifact_retention_longest_hours=_int(
                "PPTGEN_ARTIFACT_RETENTION_LONGEST_HOURS",
                "artifact_retention_longest_hours", 168,
            ),
            artifact_retention_medium_hours=_int(
                "PPTGEN_ARTIFACT_RETENTION_MEDIUM_HOURS",
                "artifact_retention_medium_hours", 72,
            ),
            artifact_retention_shorter_hours=_int(
                "PPTGEN_ARTIFACT_RETENTION_SHORTER_HOURS",
                "artifact_retention_shorter_hours", 24,
            ),
            log_level=os.environ.get("PPTGEN_LOG_LEVEL", "INFO"),
            log_json_format=os.environ.get("PPTGEN_LOG_JSON_FORMAT", "").lower() in ("1", "true", "yes"),
            design_system_path=os.environ.get("PPTGEN_DESIGN_SYSTEM_PATH", ""),
            default_theme=os.environ.get("PPTGEN_DEFAULT_THEME", ""),
            allow_draft_artifacts=_bool("PPTGEN_ALLOW_DRAFT_ARTIFACTS", False),
            analytics_dir=os.environ.get("PPTGEN_ANALYTICS_DIR", ""),
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_settings: RuntimeSettings | None = None


def get_settings() -> RuntimeSettings:
    """Return the process-wide :class:`RuntimeSettings` singleton.

    Loaded from environment variables on first call; subsequent calls return
    the cached instance.  Use :func:`override_settings` in tests.
    """
    global _settings
    if _settings is None:
        _settings = RuntimeSettings.from_env()
    return _settings


def override_settings(s: RuntimeSettings | None) -> None:
    """Replace the settings singleton.

    Pass ``None`` to reset to environment-derived defaults.

    **For use in tests only.**  Call from an autouse fixture or teardown::

        from pptgen.config import override_settings
        override_settings(RuntimeSettings(max_input_bytes=1000))
        # … test …
        override_settings(None)  # always reset
    """
    global _settings
    _settings = s
