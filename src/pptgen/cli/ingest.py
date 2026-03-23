"""pptgen ingest command.

Reads a structured source file through a named connector and prints
normalised pipeline-ready text to stdout.

Usage::

    pptgen ingest <connector_type> <input_file> [--debug]

Examples::

    pptgen ingest transcript notes/meeting.txt
    pptgen ingest ado exports/sprint12.json
    pptgen ingest metrics data/devops_metrics.json
    pptgen ingest transcript notes/meeting.txt --debug

The normalised text output is suitable for piping directly into
``generate_presentation()`` or for review before generation.
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..connectors import SUPPORTED_CONNECTORS, UnknownConnectorError, get_connector


def ingest_command(
    connector_type: str = typer.Argument(
        ...,
        help=(
            f"Connector type to use.  "
            f"Supported: {', '.join(sorted(SUPPORTED_CONNECTORS))}."
        ),
    ),
    input_file: Path = typer.Argument(
        ...,
        help="Path to the source file to ingest.",
        exists=False,  # Validated manually for a clearer error message.
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Print connector metadata alongside the normalised text.",
    ),
) -> None:
    """Ingest a structured source file and print normalised pipeline text."""
    # --- Validate connector type ---
    try:
        connector = get_connector(connector_type)
    except UnknownConnectorError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Validate input file ---
    if not input_file.exists():
        typer.echo(f"Error: input file not found: {input_file}", err=True)
        raise typer.Exit(code=1)

    if not input_file.is_file():
        typer.echo(f"Error: '{input_file}' is not a file.", err=True)
        raise typer.Exit(code=1)

    # --- Run connector ---
    try:
        output = connector.normalize(input_file)
    except (ValueError, OSError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)

    # --- Debug metadata summary ---
    if debug:
        typer.echo(f"connector   : {connector_type}", err=True)
        typer.echo(f"source      : {input_file}", err=True)
        if output.metadata:
            typer.echo("metadata    :", err=True)
            for key, value in sorted(output.metadata.items()):
                typer.echo(f"  {key}: {value}", err=True)
        typer.echo("---", err=True)

    # --- Print normalised text to stdout ---
    typer.echo(output.text)
