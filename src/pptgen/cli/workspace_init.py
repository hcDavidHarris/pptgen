"""pptgen workspace init command.

Initialises a pptgen workspace directory with the standard folder structure.

Usage:
    pptgen workspace init
    pptgen workspace init --path /projects/team/pptgen_workspace
"""

from __future__ import annotations

from pathlib import Path

import typer

workspace_app = typer.Typer(help="Workspace management commands.")

_WORKSPACE_DIRS = [
    "ado_exports",
    "notes",
    "decks",
    "validated",
    "output",
]


@workspace_app.command(name="init")
def init(
    path: Path = typer.Option(
        Path("workspace"),
        "--path",
        "-p",
        help="Root path for the workspace directory. Defaults to ./workspace",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Create workspace even if the directory already exists.",
    ),
) -> None:
    """Initialise a pptgen workspace directory structure.

    Creates the following layout:

    \b
    workspace/
    ├─ ado_exports/   raw data from Azure DevOps and external systems
    ├─ notes/         structured summaries and meeting notes
    ├─ decks/         generated pptgen YAML deck files
    ├─ validated/     YAML decks that have passed validation
    └─ output/        generated .pptx presentation files
    """
    if path.exists() and not force:
        # Check if it's already initialised
        existing = [d for d in _WORKSPACE_DIRS if (path / d).exists()]
        if existing:
            typer.echo(f"Workspace already exists at: {path}")
            typer.echo(f"  Directories present: {', '.join(existing)}")
            typer.echo("  Use --force to reinitialise.")
            return

    created = []
    for dir_name in _WORKSPACE_DIRS:
        dir_path = path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        created.append(dir_name)

    typer.echo(f"Workspace initialised: {path}/")
    for d in created:
        typer.echo(f"  + {d}/")

    typer.echo("\nNext steps:")
    typer.echo(f"  1. Add notes or ADO exports to {path}/notes/ or {path}/ado_exports/")
    typer.echo(f"  2. Generate a deck: pptgen deck scaffold --output {path}/decks/my_deck.yaml")
    typer.echo(f"  3. Validate:        pptgen validate --input {path}/decks/my_deck.yaml")
    typer.echo(f"  4. Build:           pptgen build --input {path}/decks/my_deck.yaml")
