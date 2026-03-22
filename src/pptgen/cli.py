"""pptgen CLI.

Commands:
    pptgen build --input deck.yaml [--output path/to/output.pptx]
    pptgen validate --input deck.yaml
    pptgen list-templates
"""

from __future__ import annotations

from pathlib import Path

import typer

from .errors import PptgenError
from .loaders.yaml_loader import load_deck
from .registry.registry import TemplateRegistry
from .render import render_deck
from .validators.deck_validator import validate_deck

app = typer.Typer(
    name="pptgen",
    help="Template-driven PowerPoint generation platform.",
    add_completion=False,
)

_REGISTRY_PATH = Path(__file__).parent.parent.parent / "templates" / "registry.yaml"


def _load_registry() -> TemplateRegistry:
    return TemplateRegistry.from_file(_REGISTRY_PATH)


@app.command()
def build(
    input: Path = typer.Option(..., "--input", "-i", help="Path to the deck YAML file."),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output .pptx path.  Defaults to output/<deck-title>.pptx.",
    ),
) -> None:
    """Render a YAML deck file to a .pptx presentation."""
    try:
        registry = _load_registry()
        deck, raw = load_deck(input)
        result = validate_deck(deck, registry, raw)

        if not result.valid:
            typer.echo("Validation FAILED:", err=True)
            for error in result.errors:
                typer.echo(f"  ERROR: {error}", err=True)
            raise typer.Exit(code=1)

        for warning in result.warnings:
            typer.echo(f"  WARNING: {warning}")

        entry = registry.get(deck.deck.template)
        template_path = _REGISTRY_PATH.parent.parent / entry.path

        if output is None:
            safe_title = deck.deck.title.replace(" ", "_").replace("/", "_")
            output = Path("output") / f"{safe_title}.pptx"

        render_deck(deck, template_path, output)
        typer.echo(f"Built: {output}")

    except PptgenError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command()
def validate(
    input: Path = typer.Option(..., "--input", "-i", help="Path to the deck YAML file."),
) -> None:
    """Validate a YAML deck file without rendering."""
    try:
        registry = _load_registry()
        deck, raw = load_deck(input)
        result = validate_deck(deck, registry, raw)

        for warning in result.warnings:
            typer.echo(f"  WARNING: {warning}")

        if result.valid:
            typer.echo(f"Validation PASSED ({len(deck.slides)} slides)")
        else:
            typer.echo("Validation FAILED:", err=True)
            for error in result.errors:
                typer.echo(f"  ERROR: {error}", err=True)
            raise typer.Exit(code=1)

    except PptgenError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command(name="list-templates")
def list_templates() -> None:
    """List all registered templates."""
    try:
        registry = _load_registry()
        entries = registry.all()
        if not entries:
            typer.echo("No templates registered.")
            return
        for entry in sorted(entries, key=lambda e: e.template_id):
            typer.echo(f"  {entry.template_id}  [{entry.status}]  v{entry.version}")
    except PptgenError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
