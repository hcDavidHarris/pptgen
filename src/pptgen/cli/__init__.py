"""pptgen CLI.

Commands:
    pptgen build --input deck.yaml [--output path/to/output.pptx]
    pptgen validate --input deck.yaml
    pptgen list-templates
    pptgen generate <input_file> [--output <path>] [--debug]
    pptgen deck scaffold [--template <id>] [--output <path>]
    pptgen template inspect --template <id>
    pptgen example list [--library <name>]
    pptgen workspace init [--path <dir>]
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..errors import PptgenError
from ..loaders.yaml_loader import load_deck
from ..registry.registry import TemplateRegistry
from ..render import render_deck
from ..validators.deck_validator import validate_deck
from .deck_scaffold import deck_app
from .example_commands import example_app
from .generate import generate_command
from .template_inspect import template_app
from .workspace_init import workspace_app

app = typer.Typer(
    name="pptgen",
    help="Template-driven PowerPoint generation platform.",
    add_completion=False,
)

# Register sub-apps
app.add_typer(deck_app, name="deck")
app.add_typer(example_app, name="example")
app.add_typer(template_app, name="template")
app.add_typer(workspace_app, name="workspace")

# Register top-level commands defined in sub-modules
app.command("generate")(generate_command)

_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "templates" / "registry.yaml"


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
    explain: bool = typer.Option(
        False, "--explain", help="Show detailed explanations for errors and warnings."
    ),
) -> None:
    """Validate a YAML deck file without rendering."""
    try:
        registry = _load_registry()
        deck, raw = load_deck(input)
        result = validate_deck(deck, registry, raw)

        for warning in result.warnings:
            typer.echo(f"  WARNING: {warning}")
            if explain:
                _explain_warning(warning)

        if result.valid:
            typer.echo(f"Validation PASSED ({len(deck.slides)} slides)")
        else:
            typer.echo("Validation FAILED:", err=True)
            for error in result.errors:
                typer.echo(f"  ERROR: {error}", err=True)
                if explain:
                    _explain_error(error)
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


# ---------------------------------------------------------------------------
# Validation explanation helpers
# ---------------------------------------------------------------------------

_ERROR_EXPLANATIONS: dict[str, str] = {
    "is not registered": (
        "  → The template ID in deck.template does not exist in templates/registry.yaml.\n"
        "  → Run 'pptgen list-templates' to see registered template IDs.\n"
        "  → Default template: ops_review_v1"
    ),
    "duplicate slide id": (
        "  → Two slides share the same 'id' value. Slide IDs must be unique.\n"
        "  → Remove or rename one of the duplicate IDs."
    ),
    "maximum 4 metrics allowed": (
        "  → metric_summary slides support a maximum of 4 metrics (2×2 grid).\n"
        "  → Split excess metrics into a second metric_summary slide."
    ),
}

_WARNING_EXPLANATIONS: dict[str, str] = {
    "coerced to string": (
        "  → The value was written as an unquoted number in YAML (e.g. value: 99.9).\n"
        "  → Quote it: value: \"99.9\"\n"
        "  → This prevents unexpected type coercion."
    ),
    "consider splitting": (
        "  → This slide has more bullets than recommended (max 6).\n"
        "  → Consider splitting at a natural break point.\n"
        "  → Add a section slide before each half if appropriate."
    ),
    "may be truncated": (
        "  → The metric label is longer than the recommended 40-character maximum.\n"
        "  → Shorten it to avoid truncation in the template."
    ),
    "consider using a bullets slide": (
        "  → A metric_summary slide with only one metric wastes layout space.\n"
        "  → Use a bullets slide with the metric as a bullet point instead."
    ),
}


def _explain_error(error: str) -> None:
    for key, explanation in _ERROR_EXPLANATIONS.items():
        if key in error:
            typer.echo(explanation)
            return


def _explain_warning(warning: str) -> None:
    for key, explanation in _WARNING_EXPLANATIONS.items():
        if key in warning:
            typer.echo(explanation)
            return
