"""YAML deck loader.

Responsibilities:
    1. Read a YAML file from disk.
    2. Parse it into a raw Python dict via PyYAML.
    3. Validate the dict against the DeckFile Pydantic model.

The loader returns both the typed DeckFile and the original raw dict.
The raw dict is passed to the validator so it can detect type coercions
(e.g. an unquoted metric value that PyYAML parsed as a float) and emit
warnings rather than hard failures.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from ..errors import ParseError, YAMLLoadError
from ..models.deck import DeckFile


def load_yaml_file(path: Path) -> dict:
    """Read *path* and return the parsed YAML as a raw dictionary.

    Raises:
        YAMLLoadError: if the file cannot be read or PyYAML rejects it.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise YAMLLoadError(f"Cannot read file '{path}': {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise YAMLLoadError(f"YAML parse error in '{path}': {exc}") from exc

    if not isinstance(data, dict):
        raise YAMLLoadError(
            f"Expected a YAML mapping at the top level of '{path}', "
            f"got {type(data).__name__}"
        )

    return data


# Fields that belong inside DeckMetadata and may appear at the top level
# of a Phase 9 root-format deck.
_DECK_META_FIELDS: frozenset[str] = frozenset({
    "title", "subtitle", "author", "template",
    "version", "date", "status", "description", "tags",
})


def _normalize_deck_root_shape(data: dict) -> dict:
    """Normalize a Phase 9 root-format deck to the internal deck + slides shape.

    Phase 9 structured decks may omit the ``deck:`` wrapper and instead place
    metadata fields (``title``, ``template``, ``author``, etc.) at the top
    level alongside ``slides``.  This function detects that shape and promotes
    those fields into a ``deck`` block before Pydantic validation runs.

    Trigger: ``slides`` present **and** ``deck`` absent.

    If ``deck`` is already present the data is returned unchanged, preserving
    full backward compatibility with existing legacy input.

    Required ``DeckMetadata`` fields that are absent from the top level receive
    sensible defaults (``title → "Untitled Deck"``, ``template → "ops_review_v1"``,
    ``author → "Unknown"``) so that minimally-specified Phase 9 decks still
    validate without forcing the author to repeat boilerplate.
    """
    if "deck" in data or "slides" not in data:
        return data  # already internal shape, or missing slides — let validator handle

    deck_block: dict = {}
    for field in _DECK_META_FIELDS:
        if field in data:
            deck_block[field] = data[field]

    # Defaults for DeckMetadata required fields
    deck_block.setdefault("title", "Untitled Deck")
    deck_block.setdefault("template", "ops_review_v1")
    deck_block.setdefault("author", "Unknown")

    # Remaining keys (slides, primitive, theme, content, layout, slots, …)
    normalized = {k: v for k, v in data.items() if k not in _DECK_META_FIELDS}
    normalized["deck"] = deck_block
    return normalized


def parse_deck(raw_data: dict) -> DeckFile:
    """Validate *raw_data* against the DeckFile model and return a typed object.

    Applies :func:`_normalize_deck_root_shape` before validation so that both
    the legacy ``deck + slides`` shape and the Phase 9 root shape
    (``title / theme / slides`` at top level) are accepted.

    All structural errors (missing required fields, unknown fields, wrong
    types, empty required arrays) are surfaced here as a ParseError with
    human-readable messages derived from Pydantic's ValidationError.

    Raises:
        ParseError: if the data does not conform to the DeckFile schema.
    """
    normalised = _normalize_deck_root_shape(raw_data)
    try:
        return DeckFile.model_validate(normalised)
    except ValidationError as exc:
        messages = []
        for error in exc.errors():
            # Build a dotted location string, e.g. "slides.2.metrics.0.label"
            loc = ".".join(str(part) for part in error["loc"])
            messages.append(f"{loc}: {error['msg']}")
        detail = "\n".join(f"  - {m}" for m in messages)
        raise ParseError(f"Deck structure is invalid:\n{detail}") from exc


def load_deck(path: Path) -> tuple[DeckFile, dict]:
    """Load *path*, parse it, and return ``(deck, raw_data)``.

    The raw_data dict is returned alongside the typed model so that the
    validator can inspect original YAML values for coercion warnings.

    Raises:
        YAMLLoadError: if the file cannot be read or parsed.
        ParseError:    if the content does not match the DeckFile schema.
    """
    raw = load_yaml_file(path)
    deck = parse_deck(raw)
    return deck, raw
