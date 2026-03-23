"""API service helpers.

Thin wrappers around existing pptgen modules so routes.py stays focused on
HTTP concerns.  No new business logic lives here — every call ultimately
delegates to an existing module.
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from ..pipeline import PipelineError, PipelineResult, generate_presentation
from ..playbook_engine.execution_strategy import VALID_STRATEGIES
from ..registry.registry import TemplateRegistry
from ..input_router.routing_table_loader import load_routing_table


_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"


def _generate_request_id() -> str:
    """Return a new UUID4 string for per-request tracing."""
    return str(uuid.uuid4())


class APIError(Exception):
    """Raised by service helpers to signal a 4xx-level client error."""

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
) -> PipelineResult:
    """Validate inputs and run the generation pipeline.

    Args:
        text:        Raw input text.
        mode:        Execution mode string.
        template_id: Optional template ID override.
        artifacts:   Whether to export pipeline artifacts.
        preview_only: Skip rendering if ``True``.

    Returns:
        :class:`~pptgen.pipeline.PipelineResult`.

    Raises:
        APIError: For invalid *mode* or *template_id*.
        PipelineError: Propagated from the pipeline for other failures.
    """
    if mode not in VALID_STRATEGIES:
        raise APIError(
            f"Unknown mode '{mode}'.  Valid modes: {', '.join(sorted(VALID_STRATEGIES))}.",
            status_code=400,
        )

    # Resolve output path — None for preview-only requests.
    output_path: Path | None = None
    if not preview_only:
        tmp_dir = Path(tempfile.gettempdir()) / "pptgen_api" / uuid.uuid4().hex
        tmp_dir.mkdir(parents=True, exist_ok=True)
        output_path = tmp_dir / "output.pptx"

    # Artifact directory alongside the temp output when requested.
    artifacts_dir: Path | None = None
    if artifacts and output_path is not None:
        artifacts_dir = output_path.parent / "artifacts"

    return generate_presentation(
        text,
        output_path=output_path,
        template_id=template_id,
        mode=mode,
        artifacts_dir=artifacts_dir,
    )
