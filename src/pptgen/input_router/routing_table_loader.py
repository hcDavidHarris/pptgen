"""Routing table loader.

Loads and parses ``docs/ai-playbooks/routing_table.yaml`` into a clean
list of :class:`RouteEntry` dataclasses.

The loader is intentionally decoupled from the classifier — it provides
*metadata* about routes (playbook paths, example patterns, follow-up steps)
that will be consumed by Stage 2's playbook execution engine.  The
classifier uses its own hardcoded signal map and does not call this loader
at classification time.

Usage::

    from pptgen.input_router.routing_table_loader import load_routing_table

    entries = load_routing_table()          # uses default path
    entries = load_routing_table(path)      # explicit path for testing
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


#: Default location of the routing table, relative to this file's package root.
_DEFAULT_PATH = (
    Path(__file__).parent.parent.parent.parent  # repo root
    / "docs"
    / "ai-playbooks"
    / "routing_table.yaml"
)


@dataclass(frozen=True)
class RouteEntry:
    """Parsed representation of a single route from the routing table.

    Attributes:
        route_id:        Snake-case identifier (e.g. ``meeting_notes_to_eos_rocks``).
        playbook_id:     Hyphen-separated identifier derived from the playbook
                         filename (e.g. ``meeting-notes-to-eos-rocks``).
        input_types:     Tuple of input type strings this route handles.
        tags:            Tuple of tag strings for the route.
        description:     Human-readable description of the route.
        example_pattern: Relative path to the reference example YAML.
        output_yaml:     Default output path for the generated deck.
        playbook_path:   Relative path to the playbook Markdown file.
    """

    route_id: str
    playbook_id: str
    input_types: tuple[str, ...]
    tags: tuple[str, ...]
    description: str
    example_pattern: str
    output_yaml: str
    playbook_path: str


class RoutingTableError(Exception):
    """Raised when the routing table file cannot be loaded or parsed."""

    from pptgen.errors import ErrorCategory
    category = ErrorCategory.CONFIGURATION


def _playbook_id_from_path(playbook_path: str) -> str:
    """Derive the playbook identifier from a playbook file path.

    ``docs/ai-playbooks/meeting-notes-to-eos-rocks.md``
    →  ``meeting-notes-to-eos-rocks``
    """
    return Path(playbook_path).stem


def load_routing_table(path: Path | None = None) -> list[RouteEntry]:
    """Load and parse the pptgen AI routing table.

    Args:
        path: Path to the routing table YAML file.  Defaults to
              ``docs/ai-playbooks/routing_table.yaml`` relative to the
              repository root.

    Returns:
        List of :class:`RouteEntry` instances, one per route in the file.

    Raises:
        RoutingTableError: If the file is missing, unreadable, or malformed.
    """
    resolved = path or _DEFAULT_PATH

    if not resolved.exists():
        raise RoutingTableError(
            f"Routing table not found: '{resolved}'. "
            "Ensure docs/ai-playbooks/routing_table.yaml exists."
        )

    try:
        raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RoutingTableError(
            f"Failed to parse routing table '{resolved}': {exc}"
        ) from exc

    if not isinstance(raw, dict) or "routes" not in raw:
        raise RoutingTableError(
            f"Routing table '{resolved}' must contain a top-level 'routes' key."
        )

    entries: list[RouteEntry] = []
    for idx, item in enumerate(raw["routes"]):
        try:
            entries.append(
                RouteEntry(
                    route_id=item["route_id"],
                    playbook_id=_playbook_id_from_path(item["playbook"]),
                    input_types=tuple(item.get("input_type", [])),
                    tags=tuple(item.get("tags", [])),
                    description=item.get("description", ""),
                    example_pattern=item.get("example_pattern", ""),
                    output_yaml=item.get("output_yaml", ""),
                    playbook_path=item["playbook"],
                )
            )
        except (KeyError, TypeError) as exc:
            raise RoutingTableError(
                f"Malformed route entry at index {idx}: {exc}"
            ) from exc

    return entries
