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


def parse_deck(raw_data: dict) -> DeckFile:
    """Validate *raw_data* against the DeckFile model and return a typed object.

    All structural errors (missing required fields, unknown fields, wrong
    types, empty required arrays) are surfaced here as a ParseError with
    human-readable messages derived from Pydantic's ValidationError.

    Raises:
        ParseError: if the data does not conform to the DeckFile schema.
    """
    try:
        return DeckFile.model_validate(raw_data)
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
