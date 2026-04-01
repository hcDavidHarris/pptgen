"""Startup validation for the pptgen platform.

Call :func:`validate_startup` before serving requests (API lifespan hook) or
at the top of a CLI command to surface misconfigurations early.

Usage::

    from pptgen.config import get_settings
    from pptgen.runtime.startup import validate_startup, assert_startup_healthy

    settings = get_settings()

    # Non-fatal (CLI — allows offline usage):
    failures = validate_startup(settings)
    for f in failures:
        print(f"WARNING: {f}", file=sys.stderr)

    # Fatal (API lifespan — refuses to start if unhealthy):
    assert_startup_healthy(settings)
"""

from __future__ import annotations

from pathlib import Path

from .workspace import WorkspaceManager

# Template registry path — must stay in sync with generation_pipeline.py and
# api/service.py.  Relative anchor: src/pptgen/runtime/ → repo root → templates/
_REGISTRY_PATH = (
    Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"
)


def validate_startup(settings) -> list[str]:
    """Run pre-flight checks and return a list of failure reasons.

    An empty list means all checks passed.  Callers can treat failures as
    warnings (CLI) or fatal errors (API).

    Checks performed:

    1. Template registry file exists and is readable.
    2. Workspace base directory is writable.
    3. Provider-aware credential check: ``anthropic`` requires ``PPTGEN_MODEL_API_KEY``;
       ``ollama`` does not; unknown providers are rejected.
    4. ``max_input_bytes`` is a positive integer.

    Args:
        settings: A :class:`~pptgen.config.RuntimeSettings` instance.

    Returns:
        List of human-readable failure descriptions.  Empty if healthy.
    """
    failures: list[str] = []

    # 1. Template registry must exist and be readable
    if not _REGISTRY_PATH.exists():
        failures.append(f"Template registry not found: {_REGISTRY_PATH}")
    else:
        try:
            _REGISTRY_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            failures.append(f"Template registry unreadable: {exc}")

    # 2. Workspace base must be writable
    mgr = WorkspaceManager.from_settings(settings)
    if not mgr.is_base_writable():
        failures.append(
            f"Workspace base not writable: {settings.workspace_base_path}"
        )

    # 3. Provider-aware credential check.
    #    Each provider has its own requirements — do not apply a blanket rule.
    _provider = settings.model_provider
    if settings.enable_ai_mode:
        if _provider == "anthropic":
            if not settings.model_api_key:
                failures.append(
                    f"PPTGEN_MODEL_API_KEY required when "
                    f"model_provider='{_provider}'"
                )
        elif _provider == "ollama":
            pass  # Ollama uses local HTTP — no API key required
        elif _provider in ("", "mock"):
            pass  # Default/mock mode — no credentials needed
        else:
            failures.append(
                f"Unknown model_provider '{_provider}'. "
                f"Valid values: 'mock', 'anthropic', 'ollama'."
            )

    # 4. Input size limit must be positive
    if settings.max_input_bytes <= 0:
        failures.append("max_input_bytes must be a positive integer")

    # 5. Job DB directory must be writable (Stage 6B)
    job_db_dir = settings.job_db_file.parent
    try:
        job_db_dir.mkdir(parents=True, exist_ok=True)
        probe = job_db_dir / ".job_db_write_probe"
        probe.touch()
        probe.unlink()
    except OSError as exc:
        failures.append(
            f"Job DB directory not writable: {job_db_dir} ({exc})"
        )

    # 6. Artifact store base must be writable (Stage 6C)
    from ..artifacts.storage import ArtifactStorage
    artifact_storage = ArtifactStorage.from_settings(settings)
    if not artifact_storage.is_base_writable():
        failures.append(
            f"Artifact store base not writable: {settings.artifact_store_path}"
        )

    return failures


def assert_startup_healthy(settings) -> None:
    """Raise :exc:`RuntimeError` if any startup checks fail.

    Collects all failures from :func:`validate_startup` and raises a single
    :exc:`RuntimeError` listing them all, so the operator sees every problem
    at once rather than fixing them one at a time.

    Args:
        settings: A :class:`~pptgen.config.RuntimeSettings` instance.

    Raises:
        RuntimeError: If one or more startup checks fail.
    """
    failures = validate_startup(settings)
    if failures:
        bullet = "\n  - ".join(failures)
        raise RuntimeError(f"pptgen startup validation failed:\n  - {bullet}")
