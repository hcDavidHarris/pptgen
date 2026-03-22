"""Validate all example YAML decks.

This test suite ensures every file in examples/ passes `pptgen validate`.
It is the test-layer enforcement of the invariant: all example YAML files
must pass pptgen validate with no errors.

A CI failure here means an example was added or edited without being
validated.  Fix by correcting the YAML and re-running `pptgen validate`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.loaders.yaml_loader import load_deck
from pptgen.registry.registry import TemplateRegistry
from pptgen.validators.deck_validator import validate_deck


_PROJECT_ROOT = Path(__file__).parent.parent
_REGISTRY_PATH = _PROJECT_ROOT / "templates" / "registry.yaml"
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"

#: YAML files that are metadata/catalogue files, not deck definitions.
_NON_DECK_STEMS = {"catalog"}


def _collect_example_yamls() -> list[Path]:
    """Return all example YAML deck files, excluding catalogue metadata."""
    return sorted(
        p
        for p in _EXAMPLES_DIR.rglob("*.yaml")
        if p.stem not in _NON_DECK_STEMS
    )


# Build the parametrize list at collection time so pytest reports each file
# as a separate test case.
_EXAMPLE_FILES = _collect_example_yamls()


@pytest.fixture(scope="module")
def registry() -> TemplateRegistry:
    return TemplateRegistry.from_file(_REGISTRY_PATH)


@pytest.mark.parametrize(
    "yaml_path",
    _EXAMPLE_FILES,
    ids=[str(p.relative_to(_EXAMPLES_DIR)) for p in _EXAMPLE_FILES],
)
def test_example_passes_validation(yaml_path: Path, registry: TemplateRegistry) -> None:
    """Every example deck must load and validate without errors."""
    deck, raw = load_deck(yaml_path)
    result = validate_deck(deck, registry, raw)
    assert result.valid, (
        f"Validation failed for {yaml_path.relative_to(_PROJECT_ROOT)}\n"
        + "\n".join(f"  ERROR: {e}" for e in result.errors)
    )
