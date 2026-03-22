"""Validation explanation helpers.

Provides human-readable explanations for pptgen validation errors and warnings.
These explanations are used by the `pptgen validate --explain` flag.

This module is imported by cli/__init__.py and is not a standalone command.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Error explanation catalogue
# ---------------------------------------------------------------------------

#: Maps a substring found in an error message → explanation text.
ERROR_EXPLANATIONS: dict[str, str] = {
    "is not registered in the template registry": (
        "The 'template' field in your deck references a template ID that does not\n"
        "exist in templates/registry.yaml.\n"
        "\n"
        "Fix:\n"
        "  1. Run 'pptgen list-templates' to see registered IDs.\n"
        "  2. Update deck.template to use a registered ID.\n"
        "  3. Default safe choice: ops_review_v1"
    ),
    "duplicate slide id": (
        "Two or more slides share the same 'id' value. Slide IDs must be unique\n"
        "within a deck.\n"
        "\n"
        "Fix:\n"
        "  1. Find the slides with the duplicate ID.\n"
        "  2. Rename one of them (or remove the ID if it is not needed)."
    ),
    "maximum 4 metrics allowed": (
        "A metric_summary slide may contain at most 4 metrics (2×2 grid layout).\n"
        "\n"
        "Fix:\n"
        "  1. Split the metrics across two metric_summary slides.\n"
        "  2. Place both slides under the same section for context."
    ),
    "Field required": (
        "A required field is missing from a slide definition.\n"
        "\n"
        "Common missing fields:\n"
        "  title slide:     title, subtitle\n"
        "  section slide:   section_title\n"
        "  bullets slide:   title, bullets\n"
        "  two_column:      title, left_content, right_content\n"
        "  metric_summary:  title, metrics\n"
        "  image_caption:   title, image_path, caption"
    ),
    "Extra inputs are not permitted": (
        "An unknown field was found in the YAML. The pptgen schema is strict:\n"
        "only documented fields are allowed.\n"
        "\n"
        "Fix:\n"
        "  1. Remove the unrecognised field.\n"
        "  2. Check the slide type reference at docs/authoring/slide_type_reference.md\n"
        "     for the list of allowed fields per slide type.\n"
        "\n"
        "Common mistakes:\n"
        "  bullet_list → use 'bullets'\n"
        "  content     → use 'bullets' or 'left_content'/'right_content'\n"
        "  body        → use 'bullets'"
    ),
    "Input should be a valid string": (
        "A list item was parsed as a mapping (dict) instead of a string.\n"
        "This happens when a bullet or column item contains a colon without quotes.\n"
        "\n"
        "Example of the problem:\n"
        "  bullets:\n"
        "    - Product: deliver the roadmap   ← YAML parses this as a dict\n"
        "\n"
        "Fix: quote the string:\n"
        "  bullets:\n"
        "    - \"Product: deliver the roadmap\""
    ),
}

# ---------------------------------------------------------------------------
# Warning explanation catalogue
# ---------------------------------------------------------------------------

#: Maps a substring found in a warning message → explanation text.
WARNING_EXPLANATIONS: dict[str, str] = {
    "was coerced to string": (
        "A value that should be a string was written as an unquoted number in YAML.\n"
        "PyYAML parses unquoted numbers as int/float, not string. The platform\n"
        "accepted it by coercing the type, but this should be fixed.\n"
        "\n"
        "Fix: quote the value:\n"
        "  version: \"1.0\"      (not version: 1.0)\n"
        "  value: \"99.9\"       (not value: 99.9)"
    ),
    "consider splitting into two slides": (
        "This slide contains more bullets than the recommended maximum of 6.\n"
        "Crowded slides are harder to read in presentations.\n"
        "\n"
        "Fix:\n"
        "  1. Find a natural break point in your bullets.\n"
        "  2. Split them into two bullets slides.\n"
        "  3. Optionally add a section slide to introduce each group."
    ),
    "may be truncated in template": (
        "A metric label exceeds the recommended 40-character maximum.\n"
        "The template placeholder has limited width and may cut off long labels.\n"
        "\n"
        "Fix: shorten the label to 40 characters or fewer."
    ),
    "may overflow placeholder": (
        "The composed metric value (value + unit) exceeds the recommended\n"
        "20-character maximum. The template placeholder may not display it fully.\n"
        "\n"
        "Fix: shorten the value string or omit the unit."
    ),
    "consider using a bullets slide instead": (
        "A metric_summary slide with only one metric wastes the layout.\n"
        "The 2×2 grid is designed for 2–4 metrics.\n"
        "\n"
        "Fix: use a bullets slide with the metric as a bullet point,\n"
        "     or add more metrics to the slide."
    ),
    "has status": (
        "The referenced template has a status other than 'approved'.\n"
        "Non-approved templates may be incomplete or experimental.\n"
        "\n"
        "Fix: use an approved template for production decks.\n"
        "     Run 'pptgen list-templates' to see approved IDs."
    ),
}


def explain_error(error: str) -> str | None:
    """Return an explanation for *error*, or None if no match is found."""
    for key, explanation in ERROR_EXPLANATIONS.items():
        if key in error:
            return explanation
    return None


def explain_warning(warning: str) -> str | None:
    """Return an explanation for *warning*, or None if no match is found."""
    for key, explanation in WARNING_EXPLANATIONS.items():
        if key in warning:
            return explanation
    return None
