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
    # API server
    # ------------------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    #: Comma-separated allowed CORS origins stored as an immutable tuple.
    api_cors_origins: tuple[str, ...] = field(
        default_factory=lambda: ("http://localhost:5173", "http://localhost:5174")
    )

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def workspace_base_path(self) -> Path:
        """Absolute path to the workspace root directory.

        Returns the configured override, or ``$TMPDIR/pptgen_api`` when
        :attr:`workspace_base` is empty.
        """
        base = self.workspace_base or str(Path(tempfile.gettempdir()) / "pptgen_api")
        return Path(base)

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
            api_host=os.environ.get("PPTGEN_API_HOST", "0.0.0.0"),
            api_port=_int("PPTGEN_API_PORT", "api_port", 8000),
            api_cors_origins=cors_origins,
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
