"""API service helpers.

Thin wrappers around existing pptgen modules so routes.py stays focused on
HTTP concerns.  No new business logic lives here — every call ultimately
delegates to an existing module.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from ..config import get_settings
from ..pipeline import PipelineError, PipelineResult, generate_presentation
from ..playbook_engine.execution_strategy import VALID_STRATEGIES
from ..registry.registry import TemplateRegistry
from ..input_router.routing_table_loader import load_routing_table
from ..runtime import RunContext
from ..runtime.workspace import WorkspaceManager


_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"


def _generate_request_id() -> str:
    """Return a new UUID4 string for per-request tracing."""
    return str(uuid.uuid4())


class APIError(Exception):
    """Raised by service helpers to signal a 4xx-level client error."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.VALIDATION

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def list_templates() -> list[str]:
    """Return sorted registered template IDs from the registry."""
    registry = TemplateRegistry.from_file(_REGISTRY_PATH)
    return sorted(e.template_id for e in registry.all())


def list_playbooks() -> list[str]:
    """Return sorted playbook IDs from the routing table."""
    entries = load_routing_table()
    return sorted(e.playbook_id for e in entries)


def run_generate(
    text: str,
    mode: str,
    template_id: str | None,
    artifacts: bool,
    preview_only: bool,
    request_id: str | None = None,
) -> tuple[PipelineResult, RunContext]:
    """Validate inputs, run the generation pipeline, and return run metadata.

    Args:
        text:         Raw input text.
        mode:         Execution mode string.
        template_id:  Optional template ID override.
        artifacts:    Whether to export pipeline artifacts.
        preview_only: Skip rendering if ``True``.
        request_id:   HTTP request identifier for the :class:`RunContext`.

    Returns:
        A tuple of (:class:`~pptgen.pipeline.PipelineResult`,
        :class:`~pptgen.runtime.RunContext`).

    Raises:
        APIError: For invalid *mode* or *template_id*.
        PipelineError: Propagated from the pipeline for other failures.
    """
    if mode not in VALID_STRATEGIES:
        raise APIError(
            f"Unknown mode '{mode}'.  Valid modes: {', '.join(sorted(VALID_STRATEGIES))}.",
            status_code=400,
        )

    settings = get_settings()
    ctx = RunContext(
        request_id=request_id,
        profile=settings.profile.value,
        mode=mode,
        template_id=template_id,
        config_fingerprint=settings.fingerprint,
    )

    # Resolve workspace and output path — None for preview-only requests.
    output_path: Path | None = None
    if not preview_only:
        mgr = WorkspaceManager.from_settings(settings)
        ws = mgr.create(ctx.run_id)
        ctx.workspace_path = str(ws.root)
        output_path = ws.output_path

    # Artifact directory alongside the workspace output when requested.
    artifacts_dir: Path | None = None
    if artifacts and output_path is not None:
        artifacts_dir = output_path.parent / "artifacts"

    result = generate_presentation(
        text,
        output_path=output_path,
        template_id=template_id,
        mode=mode,
        artifacts_dir=artifacts_dir,
    )
    return result, ctx
