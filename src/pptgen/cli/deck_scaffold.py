"""pptgen deck scaffold command.

Generates a starter YAML deck file from a template and deck type.

Usage:
    pptgen deck scaffold
    pptgen deck scaffold --template ops_review_v1 --type engineering_delivery
    pptgen deck scaffold --output workspace/decks/my_deck.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

from ..slide_registry import all_type_names

deck_app = typer.Typer(help="Deck authoring commands.")

_STARTER_TEMPLATES: dict[str, str] = {
    "engineering_delivery": """\
deck:
  title: Weekly Engineering Delivery Update
  template: {template}
  author: {author}
  version: "1.0"
  status: draft

slides:
  - type: title
    id: title_slide
    title: Weekly Engineering Delivery Update
    subtitle: Platform Team Review

  - type: section
    id: highlights_section
    section_title: Weekly Highlights

  - type: bullets
    id: highlights
    title: This Week's Highlights
    bullets:
      - Highlight 1
      - Highlight 2
      - Highlight 3

  - type: section
    id: blockers_section
    section_title: Risks and Blockers

  - type: bullets
    id: blockers
    title: Active Blockers
    bullets:
      - Blocker 1
      - Blocker 2

  - type: metric_summary
    id: metrics
    title: Delivery Metrics
    metrics:
      - label: Metric Label 1
        value: "0"
      - label: Metric Label 2
        value: "0"
      - label: Metric Label 3
        value: "0"
      - label: Metric Label 4
        value: "0"
""",
    "eos_rocks": """\
deck:
  title: EOS Quarterly Rocks
  template: {template}
  author: {author}
  version: "1.0"
  status: draft

slides:
  - type: title
    id: title_slide
    title: EOS Quarterly Rocks
    subtitle: Priorities for the Quarter

  - type: section
    id: company_rocks_section
    section_title: Company Rocks

  - type: bullets
    id: company_rocks
    title: Top Company Rocks
    bullets:
      - Company Rock 1
      - Company Rock 2
      - Company Rock 3

  - type: section
    id: team_rocks_section
    section_title: Team Rocks

  - type: two_column
    id: team_rocks
    title: Functional Priorities
    left_content:
      - "Team A: priority 1"
      - "Team A: priority 2"
    right_content:
      - "Team B: priority 1"
      - "Team B: priority 2"

  - type: bullets
    id: success_criteria
    title: Quarter-End Success Criteria
    bullets:
      - Success criteria 1
      - Success criteria 2
""",
    "kpi_dashboard": """\
deck:
  title: KPI Dashboard
  template: {template}
  author: {author}
  version: "1.0"
  status: draft

slides:
  - type: title
    id: title_slide
    title: KPI Dashboard
    subtitle: Operational Metrics Overview

  - type: section
    id: metrics_section
    section_title: Key Performance Indicators

  - type: metric_summary
    id: primary_kpis
    title: Primary KPIs
    metrics:
      - label: Metric 1
        value: "0"
      - label: Metric 2
        value: "0"
      - label: Metric 3
        value: "0"
      - label: Metric 4
        value: "0"
""",
    "blank": """\
deck:
  title: New Presentation
  template: {template}
  author: {author}
  version: "1.0"
  status: draft

slides:
  - type: title
    id: title_slide
    title: New Presentation
    subtitle: Subtitle

  - type: bullets
    id: content
    title: Key Points
    bullets:
      - Point 1
      - Point 2
      - Point 3
""",
}


@deck_app.command(name="scaffold")
def scaffold(
    deck_type: str = typer.Option(
        "blank",
        "--type",
        "-t",
        help=f"Starter deck type: {', '.join(sorted(_STARTER_TEMPLATES.keys()))}",
    ),
    template: str = typer.Option(
        "ops_review_v1",
        "--template",
        help="Template ID to use. Run 'pptgen list-templates' for options.",
    ),
    author: str = typer.Option(
        "Author Name",
        "--author",
        "-a",
        help="Deck author name.",
    ),
    output: Path = typer.Option(
        Path("deck.yaml"),
        "--output",
        "-o",
        help="Output path for the generated YAML file.",
    ),
) -> None:
    """Generate a starter YAML deck file.

    Creates a pre-populated YAML deck that you can edit and build.
    """
    if deck_type not in _STARTER_TEMPLATES:
        typer.echo(
            f"Unknown deck type '{deck_type}'. "
            f"Available types: {', '.join(sorted(_STARTER_TEMPLATES.keys()))}",
            err=True,
        )
        raise typer.Exit(code=1)

    content = _STARTER_TEMPLATES[deck_type].format(template=template, author=author)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    typer.echo(f"Scaffolded: {output}  (type={deck_type}, template={template})")
    typer.echo(f"  Next: pptgen validate --input {output}")
