"""Deck validator.

Responsibilities:
    - Semantic validation that sits above Pydantic's structural validation.
    - Returns a ValidationResult (PASS/FAIL + errors + warnings) rather than
      raising exceptions, so callers can present results to users cleanly.

What Pydantic already enforces (caught at parse_deck() time, not here):
    - Required fields present
    - Field types correct
    - extra='forbid' — unknown YAML keys rejected
    - min_length=1 — empty required strings/arrays rejected
    - SlideUnion discriminator — unsupported type values rejected

What this validator adds on top of Pydantic:
    - deck.template exists in the template registry and is approved
    - slide id values are unique across the deck
    - metric_summary: max 4 metrics per slide
    - metric_summary: content quality warnings (single metric, long labels)
    - bullets: content quality warning when bullet count > 6
    - coercion warnings when raw YAML contained non-string metric values
      or a non-string deck.version
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models.deck import DeckFile
from ..models.slides import (
    BulletsSlide,
    MetricSummarySlide,
    TwoColumnSlide,
)
from ..registry.registry import TemplateRegistry


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Outcome of a deck validation pass.

    Attributes:
        valid:    True when there are no errors (warnings do not block).
        errors:   List of error messages that prevent rendering.
        warnings: List of non-blocking quality warnings.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """One-line human-readable result string."""
        return "PASS" if self.valid else "FAIL"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def validate_deck(
    deck: DeckFile,
    registry: TemplateRegistry | None = None,
    raw_data: dict | None = None,
) -> ValidationResult:
    """Validate *deck* and return a ValidationResult.

    Args:
        deck:     Parsed DeckFile from parse_deck().
        registry: Optional TemplateRegistry for template reference checks.
                  When omitted, the template reference check is skipped.
        raw_data: Original raw dict from load_yaml_file().  When provided,
                  used to detect and warn about type coercions.

    Returns:
        ValidationResult with valid=True (PASS) or valid=False (FAIL).
    """
    errors: list[str] = []
    warnings: list[str] = []

    # --- Template registry check ---
    if registry is not None:
        _check_template(deck, registry, errors, warnings)

    # --- Slide ID uniqueness ---
    _check_slide_ids(deck, errors)

    # --- Per-slide semantic validation ---
    for i, slide in enumerate(deck.slides):
        slide_errors, slide_warnings = _validate_slide(slide, i + 1)
        errors.extend(slide_errors)
        warnings.extend(slide_warnings)

    # --- Coercion warnings (requires original raw YAML data) ---
    if raw_data is not None:
        warnings.extend(_detect_coercions(raw_data))

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_template(
    deck: DeckFile,
    registry: TemplateRegistry,
    errors: list[str],
    warnings: list[str],
) -> None:
    entry = registry.get(deck.deck.template)
    if entry is None:
        errors.append(
            f"deck.template: '{deck.deck.template}' is not registered in the "
            f"template registry"
        )
        return

    if entry.status != "approved":
        warnings.append(
            f"deck.template: '{deck.deck.template}' has status '{entry.status}' "
            f"— only 'approved' templates are recommended for production use"
        )


def _check_slide_ids(deck: DeckFile, errors: list[str]) -> None:
    seen: set[str] = set()
    for i, slide in enumerate(deck.slides):
        slide_id = getattr(slide, "id", None)
        if slide_id is None:
            continue
        if slide_id in seen:
            errors.append(
                f"slides: duplicate slide id '{slide_id}' at position {i + 1}"
            )
        else:
            seen.add(slide_id)


def _validate_slide(
    slide, slide_num: int
) -> tuple[list[str], list[str]]:
    """Dispatch to the per-type validator."""
    if isinstance(slide, MetricSummarySlide):
        return _validate_metric_summary(slide, slide_num)
    if isinstance(slide, BulletsSlide):
        return _validate_bullets(slide, slide_num)
    if isinstance(slide, TwoColumnSlide):
        return _validate_two_column(slide, slide_num)
    # TitleSlide, SectionSlide, ImageCaptionSlide: no additional checks
    return [], []


def _validate_metric_summary(
    slide: MetricSummarySlide, slide_num: int
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # Hard limit: max 4 metrics per Phase 1 contract
    if len(slide.metrics) > 4:
        errors.append(
            f"slide {slide_num} ('{slide.title}'): metrics: maximum 4 metrics "
            f"allowed per slide, found {len(slide.metrics)}"
        )

    # Quality warnings
    if len(slide.metrics) == 1:
        warnings.append(
            f"slide {slide_num} ('{slide.title}'): single metric — "
            f"consider using a bullets slide instead"
        )

    for j, metric in enumerate(slide.metrics):
        if len(metric.label) > 40:
            warnings.append(
                f"slide {slide_num}: metrics[{j}].label: label is "
                f"{len(metric.label)} characters — may be truncated in "
                f"template (recommended max: 40)"
            )
        composed = metric.value + (metric.unit or "")
        if len(composed) > 20:
            warnings.append(
                f"slide {slide_num}: metrics[{j}].value: composed value "
                f"'{composed}' is {len(composed)} characters — may overflow "
                f"placeholder (recommended max: 20)"
            )

    return errors, warnings


def _validate_bullets(
    slide: BulletsSlide, slide_num: int
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    if len(slide.bullets) > 6:
        warnings.append(
            f"slide {slide_num} ('{slide.title}'): {len(slide.bullets)} bullets "
            f"— consider splitting into two slides (recommended max: 6)"
        )
    return [], warnings


def _validate_two_column(
    slide: TwoColumnSlide, slide_num: int
) -> tuple[list[str], list[str]]:
    # No additional semantic checks beyond Pydantic for Phase 1
    return [], []


def _detect_coercions(raw_data: dict) -> list[str]:
    """Inspect *raw_data* for values that Pydantic had to coerce to string.

    Returns a list of warning messages.  Called with the original raw dict
    so we can compare actual YAML types against the expected string type.
    """
    warnings: list[str] = []

    # deck.version coercion
    deck_meta = raw_data.get("deck", {})
    if isinstance(deck_meta, dict):
        ver = deck_meta.get("version")
        if ver is not None and not isinstance(ver, str):
            warnings.append(
                f"deck.version: non-string value {ver!r} was coerced to "
                f"string — use a quoted YAML string (e.g. \"{ver}\")"
            )

    # metric_summary: metrics[n].value coercion
    for i, raw_slide in enumerate(raw_data.get("slides", [])):
        if not isinstance(raw_slide, dict):
            continue
        if raw_slide.get("type") != "metric_summary":
            continue
        for j, metric in enumerate(raw_slide.get("metrics", [])):
            if not isinstance(metric, dict):
                continue
            val = metric.get("value")
            if val is not None and not isinstance(val, str):
                warnings.append(
                    f"slide {i + 1}: metrics[{j}].value: non-string value "
                    f"{val!r} was coerced to string — use a quoted YAML "
                    f"string (e.g. \"{val}\")"
                )

    return warnings
