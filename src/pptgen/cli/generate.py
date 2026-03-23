"""pptgen generate command.

Generates a PowerPoint presentation from a raw text input file by running
the full Phase 4/5 generation pipeline.

Usage::

    pptgen generate <input_file> [--output <path>] [--template <id>] [--mode <mode>]
                                 [--artifacts] [--artifacts-dir <path>] [--debug]

Examples::

    pptgen generate notes/meeting_notes.txt
    pptgen generate notes/sprint_summary.txt --mode ai
    pptgen generate notes/adr.txt --template architecture_overview_v1 --debug
    pptgen generate notes/meeting.txt --mode ai --output output/meeting_ai.pptx --debug
    pptgen generate notes/meeting.txt --artifacts --output output/meeting.pptx --debug
    pptgen generate notes/meeting.txt --artifacts --artifacts-dir my_artifacts/
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..pipeline import PipelineError, generate_presentation
from ..playbook_engine.execution_strategy import DETERMINISTIC, VALID_STRATEGIES, ExecutionMode


def generate_command(
    input_file: Path = typer.Argument(
        ...,
        help="Path to the raw text input file (meeting notes, sprint summary, ADR, etc.).",
        exists=False,  # We handle the missing-file error ourselves for a better message
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output .pptx path.  Defaults to output/<input_stem>.pptx.",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help=(
            "Template ID override (must be registered in templates/registry.yaml).  "
            "Defaults to the playbook-specific template."
        ),
    ),
    mode: str = typer.Option(
        DETERMINISTIC,
        "--mode",
        "-m",
        help="Execution mode: 'deterministic' (default) or 'ai'.",
    ),
    artifacts: bool = typer.Option(
        False,
        "--artifacts",
        help=(
            "Export intermediate pipeline artifacts (spec.json, slide_plan.json, "
            "deck_definition.json) alongside the output file.  "
            "Default location: <output_stem>.artifacts/ next to the .pptx."
        ),
    ),
    artifacts_dir: Optional[Path] = typer.Option(
        None,
        "--artifacts-dir",
        help=(
            "Override the artifacts output directory.  "
            "Implies --artifacts when provided."
        ),
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Print a concise pipeline summary after generation.",
    ),
) -> None:
    """Generate a PowerPoint presentation from a raw text input file."""
    # --- Validate mode early ---
    try:
        ExecutionMode(mode)
    except ValueError:
        typer.echo(
            f"Error: unknown mode '{mode}'.  "
            f"Valid modes: {', '.join(sorted(VALID_STRATEGIES))}.",
            err=True,
        )
        raise typer.Exit(code=1)

    # --- Resolve and read input file ---
    if not input_file.exists():
        typer.echo(f"Error: input file not found: {input_file}", err=True)
        raise typer.Exit(code=1)

    if not input_file.is_file():
        typer.echo(f"Error: '{input_file}' is not a file.", err=True)
        raise typer.Exit(code=1)

    try:
        text = input_file.read_text(encoding="utf-8")
    except OSError as exc:
        typer.echo(f"Error: cannot read '{input_file}': {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Determine output path ---
    safe_stem = input_file.stem.replace(" ", "_").replace("/", "_")
    resolved_output: Path = output if output is not None else Path("output") / f"{safe_stem}.pptx"

    # --- Resolve artifacts directory ---
    resolved_artifacts_dir: Path | None = None
    if artifacts_dir is not None:
        resolved_artifacts_dir = artifacts_dir
    elif artifacts:
        resolved_artifacts_dir = resolved_output.parent / f"{resolved_output.stem}.artifacts"

    # --- Run pipeline ---
    try:
        result = generate_presentation(
            text,
            output_path=resolved_output,
            template_id=template,
            mode=mode,
            artifacts_dir=resolved_artifacts_dir,
        )
    except PipelineError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Debug summary ---
    if debug:
        typer.echo(f"mode        : {result.mode}")
        typer.echo(f"playbook_id : {result.playbook_id}")
        typer.echo(f"template_id : {result.template_id}")
        typer.echo(f"stage       : {result.stage}")
        if result.slide_plan is not None:
            typer.echo(f"slide_count : {result.slide_plan.slide_count}")
            typer.echo(f"slide_types : {result.slide_plan.planned_slide_types}")
        typer.echo(f"output_path : {result.output_path}")
        if result.artifact_paths:
            typer.echo(f"artifacts   : {resolved_artifacts_dir}")
            for name, path in sorted(result.artifact_paths.items()):
                typer.echo(f"  {name}: {path}")
        if result.notes:
            typer.echo(f"notes       : {result.notes}")

    typer.echo(f"Generated: {result.output_path}")
