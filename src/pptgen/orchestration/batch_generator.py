"""Batch generation orchestrator.

Processes every file in an input directory through the pptgen pipeline,
producing one ``.pptx`` output per file.  The existing single-file
:func:`~pptgen.pipeline.generate_presentation` is reused for every item —
no second pipeline is introduced.

Two input modes are supported:

``raw text mode`` (default)
    Each file is read as UTF-8 text and passed directly to the pipeline.

``connector mode`` (when *connector_type* is supplied)
    Each file is first normalised via
    :func:`~pptgen.connectors.get_connector`, then the resulting text is
    passed to the pipeline.  Per-file connector errors do *not* abort the
    batch; they are recorded in :attr:`BatchItemResult.error`.

Files are processed in deterministic (alphabetically sorted) order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..connectors import UnknownConnectorError, get_connector
from ..pipeline import PipelineError, generate_presentation
from ..playbook_engine.execution_strategy import DETERMINISTIC, ExecutionMode


@dataclass
class BatchItemResult:
    """Result for a single file in a batch run.

    Attributes:
        input_path:    Source file that was processed.
        output_path:   Rendered ``.pptx`` path, or ``None`` on failure.
        playbook_id:   Playbook chosen by the router, or ``None`` on failure.
        success:       Whether the file was processed without error.
        error:         Error message string if *success* is ``False``.
        artifact_paths: Artifact path mapping if artifacts were exported.
    """

    input_path: Path
    output_path: Path | None = None
    playbook_id: str | None = None
    success: bool = False
    error: str = ""
    artifact_paths: dict[str, str] | None = None


@dataclass
class BatchResult:
    """Aggregate result for a complete batch run.

    Attributes:
        total_files: Number of files discovered in the input directory.
        succeeded:   Number of files processed without error.
        failed:      Number of files that produced an error.
        outputs:     Per-file :class:`BatchItemResult` list, in processing order.
        notes:       Optional diagnostic notes (e.g. skipped subdirectories).
    """

    total_files: int
    succeeded: int
    failed: int
    outputs: list[BatchItemResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class BatchError(Exception):
    """Raised for invalid batch configuration (bad directory, bad connector, etc.)."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.SYSTEM


def generate_batch(
    input_dir: Path,
    output_dir: Path | None = None,
    connector_type: str | None = None,
    mode: str | ExecutionMode = DETERMINISTIC,
    template_id: str | None = None,
    artifacts: bool = False,
    artifacts_base_dir: Path | None = None,
) -> BatchResult:
    """Process every file in *input_dir* through the generation pipeline.

    Args:
        input_dir:         Directory containing source files.  Must exist
                           and be a directory.
        output_dir:        Directory for rendered ``.pptx`` files.  Defaults
                           to ``output/batch/``.  Created if absent.
        connector_type:    If supplied, each file is normalised via the
                           named connector before entering the pipeline.
                           Must be a key in
                           :data:`~pptgen.connectors.SUPPORTED_CONNECTORS`.
        mode:              Execution mode — ``"deterministic"`` (default)
                           or ``"ai"``.
        template_id:       Optional template override applied to every file.
        artifacts:         If ``True``, export per-file artifacts.
        artifacts_base_dir: Base directory under which per-file artifact
                           sub-directories are created.  Defaults to
                           *output_dir* when *artifacts* is ``True``.

    Returns:
        :class:`BatchResult` with per-file outcomes and aggregate counts.

    Raises:
        BatchError: If *input_dir* does not exist, is not a directory, or
                    *connector_type* is unsupported.
    """
    input_dir = Path(input_dir)
    _validate_input_dir(input_dir)

    if connector_type is not None:
        _validate_connector_type(connector_type)

    resolved_output_dir: Path = Path(output_dir) if output_dir else Path("output") / "batch"
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    files = _discover_files(input_dir)
    notes: list[str] = []

    if not files:
        notes.append(f"No files found in '{input_dir}'.")

    outputs: list[BatchItemResult] = []
    for path in files:
        item = _process_file(
            path=path,
            output_dir=resolved_output_dir,
            connector_type=connector_type,
            mode=mode,
            template_id=template_id,
            artifacts=artifacts,
            artifacts_base_dir=artifacts_base_dir or (resolved_output_dir if artifacts else None),
        )
        outputs.append(item)

    succeeded = sum(1 for o in outputs if o.success)
    failed = len(outputs) - succeeded

    return BatchResult(
        total_files=len(files),
        succeeded=succeeded,
        failed=failed,
        outputs=outputs,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_input_dir(path: Path) -> None:
    if not path.exists():
        raise BatchError(f"Input directory not found: '{path}'.")
    if not path.is_dir():
        raise BatchError(f"'{path}' is not a directory.")


def _validate_connector_type(connector_type: str) -> None:
    try:
        get_connector(connector_type)
    except UnknownConnectorError as exc:
        raise BatchError(str(exc)) from exc


def _discover_files(directory: Path) -> list[Path]:
    """Return regular files in *directory*, sorted by name for determinism."""
    return sorted(
        (p for p in directory.iterdir() if p.is_file()),
        key=lambda p: p.name,
    )


def _process_file(
    path: Path,
    output_dir: Path,
    connector_type: str | None,
    mode: str | ExecutionMode,
    template_id: str | None,
    artifacts: bool,
    artifacts_base_dir: Path | None,
) -> BatchItemResult:
    """Run the pipeline for a single file; catch and record any errors."""
    output_path = output_dir / f"{path.stem}.pptx"
    item = BatchItemResult(input_path=path, output_path=output_path)

    # Resolve per-file artifact directory.
    file_artifacts_dir: Path | None = None
    if artifacts and artifacts_base_dir is not None:
        file_artifacts_dir = artifacts_base_dir / f"{path.stem}.artifacts"

    try:
        text = _read_text(path, connector_type)
        result = generate_presentation(
            text,
            output_path=output_path,
            template_id=template_id,
            mode=mode,
            artifacts_dir=file_artifacts_dir,
        )
        item.success = True
        item.playbook_id = result.playbook_id
        item.artifact_paths = result.artifact_paths
    except Exception as exc:  # noqa: BLE001 — catch-all intentional for batch isolation
        item.success = False
        item.error = str(exc)
        item.output_path = None  # Nothing was written on failure

    return item


def _read_text(path: Path, connector_type: str | None) -> str:
    """Return pipeline-ready text from *path*."""
    if connector_type is not None:
        connector = get_connector(connector_type)
        output = connector.normalize(path)
        return output.text
    return path.read_text(encoding="utf-8")
