"""Integration tests: load an example deck from disk and validate it.

These tests exercise the full load → parse → validate pipeline against
real files in the repository, using the real template registry.

Success criteria (from the implementation spec):
  - examples/executive_update.yaml loads without error
  - it parses into a valid DeckFile
  - it passes validate_deck() with no errors
  - the template it references exists in templates/registry.yaml
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.loaders.yaml_loader import load_deck
from pptgen.models.slides import (
    BulletsSlide,
    MetricSummarySlide,
    SectionSlide,
    TitleSlide,
)
from pptgen.registry.registry import TemplateRegistry
from pptgen.validators.deck_validator import validate_deck


class TestExecutiveUpdateDeck:
    """Full pipeline test against examples/executive_update.yaml."""

    @pytest.fixture
    def executive_update(self, examples_dir: Path):
        deck, raw = load_deck(examples_dir / "executive_update.yaml")
        return deck, raw

    @pytest.fixture
    def real_registry(self, real_registry_path: Path):
        return TemplateRegistry.from_file(real_registry_path)

    def test_deck_loads_without_error(self, executive_update):
        deck, _ = executive_update
        assert deck is not None

    def test_deck_title_is_correct(self, executive_update):
        deck, _ = executive_update
        assert deck.deck.title == "Executive Update"

    def test_deck_template_is_executive_brief(self, executive_update):
        deck, _ = executive_update
        assert deck.deck.template == "executive_brief_v1"

    def test_deck_author_is_present(self, executive_update):
        deck, _ = executive_update
        assert deck.deck.author == "David Harris"

    def test_version_is_string(self, executive_update):
        """executive_update.yaml version must be a string after loading."""
        deck, raw = executive_update
        assert deck.deck.version == "1.0"
        assert isinstance(deck.deck.version, str)

    def test_deck_has_six_slides(self, executive_update):
        deck, _ = executive_update
        assert len(deck.slides) == 6

    def test_slide_types_are_correct(self, executive_update):
        deck, _ = executive_update
        types = [type(s) for s in deck.slides]
        assert types == [
            TitleSlide,
            SectionSlide,
            BulletsSlide,
            SectionSlide,
            BulletsSlide,
            MetricSummarySlide,
        ]

    def test_metric_summary_has_three_metrics(self, executive_update):
        deck, _ = executive_update
        metric_slide = deck.slides[-1]
        assert isinstance(metric_slide, MetricSummarySlide)
        assert len(metric_slide.metrics) == 3

    def test_metric_values_are_strings(self, executive_update):
        deck, _ = executive_update
        metric_slide = deck.slides[-1]
        assert isinstance(metric_slide, MetricSummarySlide)
        for metric in metric_slide.metrics:
            assert isinstance(metric.value, str)

    def test_all_slide_ids_unique(self, executive_update):
        deck, _ = executive_update
        ids = [s.id for s in deck.slides if s.id is not None]
        assert len(ids) == len(set(ids))

    def test_deck_validates_successfully(self, executive_update, real_registry):
        deck, raw = executive_update
        result = validate_deck(deck, registry=real_registry, raw_data=raw)
        assert result.valid is True, (
            f"Expected PASS but got FAIL.\nErrors: {result.errors}"
        )

    def test_deck_has_no_validation_errors(self, executive_update, real_registry):
        deck, raw = executive_update
        result = validate_deck(deck, registry=real_registry, raw_data=raw)
        assert result.errors == []

    def test_template_exists_in_real_registry(self, executive_update, real_registry):
        deck, _ = executive_update
        assert real_registry.exists(deck.deck.template), (
            f"Template '{deck.deck.template}' not found in templates/registry.yaml"
        )

    def test_template_is_approved(self, executive_update, real_registry):
        deck, _ = executive_update
        entry = real_registry.get(deck.deck.template)
        assert entry is not None
        assert entry.status == "approved"

    def test_version_coercion_warning_is_emitted(self, fixtures_dir, real_registry):
        """Coercion warning should be emitted for the unquoted version: 1.0.

        Uses tests/fixtures/version_coercion_deck.yaml which intentionally
        has version: 1.0 (unquoted float) to exercise the coercion path.
        """
        deck, raw = load_deck(fixtures_dir / "version_coercion_deck.yaml")
        # Raw YAML should have parsed the unquoted 1.0 as a float
        assert isinstance(raw["deck"]["version"], float)
        result = validate_deck(deck, registry=real_registry, raw_data=raw)
        assert any(
            "deck.version" in w and "coerced" in w for w in result.warnings
        ), f"Expected coercion warning for deck.version. Warnings: {result.warnings}"


class TestValidFixtureDeck:
    """Pipeline test against tests/fixtures/valid_deck.yaml."""

    @pytest.fixture
    def valid_deck(self, fixtures_dir: Path):
        return load_deck(fixtures_dir / "valid_deck.yaml")

    def test_valid_deck_loads(self, valid_deck):
        deck, _ = valid_deck
        assert deck is not None

    def test_valid_deck_passes_validation(self, valid_deck, test_registry):
        deck, raw = valid_deck
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is True


class TestInvalidFixtureDeck:
    """Pipeline test against tests/fixtures/invalid_deck.yaml.

    This deck is structurally valid (parses cleanly) but fails semantic
    validation: unknown template + 5-metric slide.
    """

    @pytest.fixture
    def invalid_deck(self, fixtures_dir: Path):
        return load_deck(fixtures_dir / "invalid_deck.yaml")

    def test_invalid_deck_parses_without_error(self, invalid_deck):
        """Structural parse must succeed — validation is the failure point."""
        deck, _ = invalid_deck
        assert deck is not None

    def test_invalid_deck_fails_validation(self, invalid_deck, test_registry):
        deck, raw = invalid_deck
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is False

    def test_invalid_deck_errors_are_specific(self, invalid_deck, test_registry):
        deck, raw = invalid_deck
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        error_text = " ".join(result.errors)
        assert "not registered" in error_text
        assert "maximum 4" in error_text
