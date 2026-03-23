"""pptgen generate-batch command.

Processes every file in a directory through the generation pipeline,
producing one ``.pptx`` per input file.

Usage::

    pptgen generate-batch <directory> [options]

Examples::

    pptgen generate-batch tests/fixtures/batch/text/
    pptgen generate-batch tests/fixtures/batch/ado/ --connector ado
    pptgen generate-batch tests/fixtures/batch/metrics/ --connector metrics --artifacts
    pptgen generate-batch tests/fixtures/batch/text/ --mode ai --output-dir output/ai_batch --debug
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..connectors import SUPPORTED_CONNECTORS
from ..orchestration import generate_batch
from ..orchestration.batch_generator import BatchError
from ..playbook_engine.execution_strategy import DETERMINISTIC, VALID_STRATEGIES, ExecutionMode


def generate_batch_command(
    directory: Path = typer.Argument(
        ...,
        help="Directory containing input files to process.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        help="Output directory for rendered .pptx files.  Defaults to output/batch/.",
    ),
    connector: Optional[str] = typer.Option(
        None,
        "--connector",
        "-c",
        help=(
            f"Connector type for structured source files.  "
            f"Supported: {', '.join(sorted(SUPPORTED_CONNECTORS))}."
        ),
    ),
    mode: str = typer.Option(
        DETERMINISTIC,
        "--mode",
        "-m",
        help="Execution mode: 'deterministic' (default) or 'ai'.",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Template ID override applied to every file in the batch.",
    ),
    artifacts: bool = typer.Option(
        False,
        "--artifacts",
        help="Export per-file artifacts (spec.json, slide_plan.json, deck_definition.json).",
    ),
    artifacts_dir: Optional[Path] = typer.Option(
        None,
        "--artifacts-dir",
        help=(
            "Base directory for per-file artifact sub-directories.  "
            "Defaults to output-dir when --artifacts is set."
        ),
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Print a per-file summary in addition to the final batch summary.",
    ),
) -> None:
    """Process every file in a directory and generate one presentation per file."""
    # --- Validate mode ---
    try:
        ExecutionMode(mode)
    except ValueError:
        typer.echo(
            f"Error: unknown mode '{mode}'.  "
            f"Valid modes: {', '.join(sorted(VALID_STRATEGIES))}.",
            err=True,
        )
        raise typer.Exit(code=1)

    # --artifacts-dir implies artifact export even without --artifacts flag.
    effective_artifacts = artifacts or (artifacts_dir is not None)
    resolved_artifacts_dir: Path | None = artifacts_dir  # None when not supplied

    # --- Run batch ---
    try:
        result = generate_batch(
            input_dir=directory,
            output_dir=output_dir,
            connector_type=connector,
            mode=mode,
            template_id=template,
            artifacts=effective_artifacts,
            artifacts_base_dir=resolved_artifacts_dir,
        )
    except BatchError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Per-file debug output ---
    if debug:
        for item in result.outputs:
            status = "ok" if item.success else "FAILED"
            typer.echo(f"  [{status}] {item.input_path.name}")
            if item.success:
                typer.echo(f"         output    : {item.output_path}")
                if item.playbook_id:
                    typer.echo(f"         playbook  : {item.playbook_id}")
                if item.artifact_paths:
                    arts_dir = Path(next(iter(item.artifact_paths.values()))).parent
                    typer.echo(f"         artifacts : {arts_dir}")
            else:
                typer.echo(f"         error     : {item.error}")

    # --- Final summary (always printed) ---
    if result.notes:
        for note in result.notes:
            typer.echo(f"Note: {note}")

    typer.echo(
        f"Batch complete: {result.total_files} file(s) — "
        f"{result.succeeded} succeeded, {result.failed} failed."
    )

    if result.failed > 0:
        raise typer.Exit(code=1)
