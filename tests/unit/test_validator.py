"""Unit tests for the deck validator.

Tests exercise validate_deck() via parsed DeckFile objects (produced by
parse_deck()) against a test registry fixture.  Each test targets a specific
validation rule and asserts on the ValidationResult.
"""

from __future__ import annotations

import pytest

from pptgen.loaders.yaml_loader import parse_deck
from pptgen.validators.deck_validator import ValidationResult, validate_deck


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deck(slides: list[dict], template: str = "ops_review_v1") -> dict:
    """Minimal deck raw dict for use in tests."""
    return {
        "deck": {"title": "Test Deck", "template": template, "author": "Tester"},
        "slides": slides,
    }


def _title_slide() -> dict:
    return {"type": "title", "title": "Title", "subtitle": "Subtitle"}


def _bullets_slide(count: int = 3) -> dict:
    return {
        "type": "bullets",
        "title": "Bullets",
        "bullets": [f"Item {i}" for i in range(count)],
    }


def _metric_slide(n: int, label_prefix: str = "M") -> dict:
    return {
        "type": "metric_summary",
        "title": "Metrics",
        "metrics": [{"label": f"{label_prefix}{i}", "value": str(i)} for i in range(n)],
    }


# ---------------------------------------------------------------------------
# Basic PASS / FAIL
# ---------------------------------------------------------------------------

class TestBasicValidation:
    def test_valid_deck_passes(self, test_registry):
        raw = _deck([_title_slide(), _bullets_slide()])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is True
        assert result.errors == []
        assert result.summary() == "PASS"

    def test_validation_result_summary_fail(self, test_registry):
        raw = _deck([_title_slide()], template="missing_template")
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.summary() == "FAIL"


# ---------------------------------------------------------------------------
# Template registry checks
# ---------------------------------------------------------------------------

class TestTemplateRegistryChecks:
    def test_missing_template_produces_error(self, test_registry):
        raw = _deck([_title_slide()], template="nonexistent_v1")
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is False
        assert any("not registered" in e for e in result.errors)

    def test_registered_approved_template_passes(self, test_registry):
        raw = _deck([_title_slide()], template="ops_review_v1")
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True

    def test_draft_template_produces_warning_not_error(self, test_registry):
        raw = _deck([_title_slide()], template="draft_template_v1")
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert any("draft" in w for w in result.warnings)

    def test_no_registry_skips_template_check(self):
        raw = _deck([_title_slide()], template="anything")
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=None)
        assert result.valid is True


# ---------------------------------------------------------------------------
# Slide ID uniqueness
# ---------------------------------------------------------------------------

class TestSlideIdUniqueness:
    def test_unique_ids_pass(self, test_registry):
        raw = _deck([
            {**_title_slide(), "id": "slide_1"},
            {**_bullets_slide(), "id": "slide_2"},
        ])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True

    def test_duplicate_id_produces_error(self, test_registry):
        raw = _deck([
            {**_title_slide(), "id": "duplicate_id"},
            {**_bullets_slide(), "id": "duplicate_id"},
        ])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is False
        assert any("duplicate" in e and "duplicate_id" in e for e in result.errors)

    def test_missing_ids_are_ignored(self, test_registry):
        raw = _deck([_title_slide(), _bullets_slide()])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True


# ---------------------------------------------------------------------------
# metric_summary validation
# ---------------------------------------------------------------------------

class TestMetricSummaryValidation:
    def test_one_metric_passes_with_warning(self, test_registry):
        raw = _deck([_metric_slide(1)])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert any("single metric" in w for w in result.warnings)

    def test_two_metrics_pass_cleanly(self, test_registry):
        raw = _deck([_metric_slide(2)])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert not any("single metric" in w for w in result.warnings)

    def test_four_metrics_pass(self, test_registry):
        raw = _deck([_metric_slide(4)])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert result.errors == []

    def test_five_metrics_fails(self, test_registry):
        raw = _deck([_metric_slide(5)])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is False
        assert any("maximum 4" in e for e in result.errors)

    def test_long_label_produces_warning(self, test_registry):
        long_label = "A" * 41
        raw = _deck([
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [{"label": long_label, "value": "100"}],
            }
        ])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert any("label" in w and "truncated" in w for w in result.warnings)

    def test_long_composed_value_produces_warning(self, test_registry):
        raw = _deck([
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [
                    {
                        "label": "Rate",
                        "value": "12345678901234567890",  # 20 chars
                        "unit": "x",  # composed = 21 chars
                    }
                ],
            }
        ])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert any("overflow" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Bullet count warning
# ---------------------------------------------------------------------------

class TestBulletCountWarning:
    def test_six_bullets_no_warning(self, test_registry):
        raw = _deck([_bullets_slide(6)])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert not any("bullets" in w for w in result.warnings)

    def test_seven_bullets_produces_warning(self, test_registry):
        raw = _deck([_bullets_slide(7)])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry)
        assert result.valid is True
        assert any("7 bullets" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Coercion warnings
# ---------------------------------------------------------------------------

class TestCoercionWarnings:
    def test_float_metric_value_emits_warning(self, test_registry):
        raw = _deck([
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [{"label": "Rate", "value": 99.9}],
            }
        ])
        deck = parse_deck(raw)  # coercion happens here; model accepts it
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is True
        assert any("coerced" in w and "99.9" in w for w in result.warnings)

    def test_int_metric_value_emits_warning(self, test_registry):
        raw = _deck([
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [{"label": "Count", "value": 1200}],
            }
        ])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is True
        assert any("coerced" in w for w in result.warnings)

    def test_string_metric_value_no_warning(self, test_registry):
        raw = _deck([
            {
                "type": "metric_summary",
                "title": "Metrics",
                "metrics": [{"label": "Rate", "value": "99.9%"}],
            }
        ])
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is True
        assert not any("coerced" in w for w in result.warnings)

    def test_float_deck_version_emits_warning(self, test_registry):
        raw = {
            "deck": {
                "title": "T",
                "template": "ops_review_v1",
                "author": "A",
                "version": 1.0,  # PyYAML parses unquoted 1.0 as float
            },
            "slides": [_title_slide()],
        }
        deck = parse_deck(raw)
        result = validate_deck(deck, registry=test_registry, raw_data=raw)
        assert result.valid is True
        assert any("deck.version" in w and "coerced" in w for w in result.warnings)

    def test_no_raw_data_skips_coercion_check(self, test_registry):
        raw = _deck([_bullets_slide()])
        deck = parse_deck(raw)
        # Passing raw_data=None means coercion check is skipped entirely
        result = validate_deck(deck, registry=test_registry, raw_data=None)
        assert result.valid is True
