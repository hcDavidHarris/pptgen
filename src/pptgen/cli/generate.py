"""pptgen generate command.

Generates a PowerPoint presentation from a raw text input file by running
the full Phase 4 generation pipeline.

Usage::

    pptgen generate <input_file> [--output <path>] [--template <id>] [--debug]

Examples::

    pptgen generate notes/meeting_notes.txt --output output/meeting.pptx
    pptgen generate notes/sprint_summary.txt --template executive_brief_v1
    pptgen generate notes/adr.txt --template architecture_overview_v1 --debug
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..pipeline import PipelineError, generate_presentation


def generate_command(
    input_file: Path = typer.Argument(
        ...,
        help="Path to the raw text input file (meeting notes, sprint summary, ADR, etc.).",
        exists=False,  # We handle the missing-file error ourselves for a better message
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help=(
            "Output .pptx path.  "
            "Defaults to output/<input_stem>.pptx."
        ),
    ),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help=(
            "Template ID override (must be registered in templates/registry.yaml).  "
            "Defaults to the playbook-specific template."
        ),
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Print a concise pipeline summary after generation.",
    ),
) -> None:
    """Generate a PowerPoint presentation from a raw text input file."""
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
    resolved_output: Path
    if output is not None:
        resolved_output = output
    else:
        safe_stem = input_file.stem.replace(" ", "_").replace("/", "_")
        resolved_output = Path("output") / f"{safe_stem}.pptx"

    # --- Run pipeline ---
    try:
        result = generate_presentation(
            text,
            output_path=resolved_output,
            template_id=template,
        )
    except PipelineError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Debug summary ---
    if debug:
        typer.echo(f"playbook_id : {result.playbook_id}")
        typer.echo(f"template_id : {result.template_id}")
        typer.echo(f"stage       : {result.stage}")
        if result.slide_plan is not None:
            typer.echo(f"slide_count : {result.slide_plan.slide_count}")
            typer.echo(f"slide_types : {result.slide_plan.planned_slide_types}")
        typer.echo(f"output_path : {result.output_path}")

    typer.echo(f"Generated: {result.output_path}")
