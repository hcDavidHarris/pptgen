"""pptgen example commands.

Browse and copy example decks from the repository example library.

Usage:
    pptgen example list
    pptgen example list --library eos
    pptgen example show eos_rocks
    pptgen example copy eos_rocks --output workspace/decks/eos_rocks.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

example_app = typer.Typer(help="Browse and copy example decks.")

_EXAMPLES_ROOT = Path(__file__).parent.parent.parent.parent / "examples"

#: Maps library name → subdirectory path relative to examples/
_LIBRARIES: dict[str, Path] = {
    "architecture": _EXAMPLES_ROOT / "architecture",
    "eos": _EXAMPLES_ROOT / "eos",
    "engineering_delivery": _EXAMPLES_ROOT / "engineering_delivery",
    "devops": _EXAMPLES_ROOT / "devops",
    "team_topologies": _EXAMPLES_ROOT / "team_topologies",
    "root": _EXAMPLES_ROOT,
}

#: Human-readable descriptions per library
_LIBRARY_DESCRIPTIONS: dict[str, str] = {
    "architecture": "Architecture: ADR templates, architecture decision records, system diagrams",
    "eos": "EOS leadership artifacts: rocks, scorecard, VTO, issues list, quarterly review",
    "engineering_delivery": "Engineering delivery: weekly updates, sprint summaries, backlog health, risks",
    "devops": "DevOps: DORA metrics, Three Ways, pipeline, transformation, experiment review",
    "team_topologies": "Team Topologies: team types, interaction modes, cognitive load, platform model",
    "root": "Generic: executive update, architecture overview, KPI dashboard, strategy",
}


@example_app.command(name="list")
def list_examples(
    library: str = typer.Option(
        "",
        "--library",
        "-l",
        help=f"Filter by library: {', '.join(sorted(_LIBRARIES.keys()))}",
    ),
) -> None:
    """List available example decks."""
    if library and library not in _LIBRARIES:
        typer.echo(
            f"Unknown library '{library}'. "
            f"Available: {', '.join(sorted(_LIBRARIES.keys()))}",
            err=True,
        )
        raise typer.Exit(code=1)

    libraries_to_show = {library: _LIBRARIES[library]} if library else _LIBRARIES

    for lib_name, lib_path in sorted(libraries_to_show.items()):
        if not lib_path.exists():
            continue

        yaml_files = sorted(lib_path.glob("*.yaml"))
        if not yaml_files:
            continue

        typer.echo(f"\n{lib_name}/")
        desc = _LIBRARY_DESCRIPTIONS.get(lib_name, "")
        if desc:
            typer.echo(f"  {desc}")

        for f in yaml_files:
            stem = f.stem
            # Skip non-deck files (catalog.yaml, etc.)
            if stem in ("catalog",):
                continue
            relative = f.relative_to(_EXAMPLES_ROOT)
            typer.echo(f"  {stem:<40}  examples/{relative}")


@example_app.command(name="show")
def show_example(
    name: str = typer.Argument(help="Example name (stem of the YAML file, e.g. eos_rocks)"),
) -> None:
    """Print the content of an example deck."""
    found = _find_example(name)
    if found is None:
        typer.echo(f"Example '{name}' not found. Run 'pptgen example list' to browse.", err=True)
        raise typer.Exit(code=1)
    typer.echo(found.read_text(encoding="utf-8"))


@example_app.command(name="copy")
def copy_example(
    name: str = typer.Argument(help="Example name to copy (e.g. eos_rocks)"),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Destination path for the copied deck (e.g. workspace/decks/eos_rocks.yaml)",
    ),
) -> None:
    """Copy an example deck to your workspace."""
    found = _find_example(name)
    if found is None:
        typer.echo(f"Example '{name}' not found. Run 'pptgen example list' to browse.", err=True)
        raise typer.Exit(code=1)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(found.read_text(encoding="utf-8"), encoding="utf-8")
    typer.echo(f"Copied: {found.relative_to(_EXAMPLES_ROOT.parent)}  ->  {output}")
    typer.echo(f"  Next: pptgen validate --input {output}")


def _find_example(name: str) -> Path | None:
    """Search all library directories for an example with the given stem name."""
    for lib_path in _LIBRARIES.values():
        candidate = lib_path / f"{name}.yaml"
        if candidate.exists():
            return candidate
    return None
