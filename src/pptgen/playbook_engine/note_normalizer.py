"""Deterministic note normalization for labeled note-style input.

Converts operational note text that uses recognized label-colon headings
(e.g. ``Problems:``, ``Next Step:``, ``Focus Areas:``) into a structured
intermediate form before spec generation.

Design constraints
------------------
- Entirely deterministic: same input always produces same output.
- No regex, no ML, no external dependencies.
- Only recognizes labels explicitly listed in ``_SEMANTIC_MAP``.
- Unknown labels still produce sections; semantic_type is ``"general"``.
- Safe for any string input including empty strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

@dataclass
class NormalizedSection:
    """A single labeled block of content extracted from note text."""

    label: str
    semantic_type: str
    items: list[str] = field(default_factory=list)


@dataclass
class NormalizedNotes:
    """Full normalized representation of a labeled note document."""

    title: str | None
    sections: list[NormalizedSection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Semantic label registry
# ---------------------------------------------------------------------------

# Maps lower-cased label → semantic_type for the downstream spec builder.
# Keep this small and stable; add new mappings when new label conventions emerge.
_SEMANTIC_MAP: dict[str, str] = {
    "problems": "risks",
    "risks": "risks",
    "concerns": "risks",
    "next step": "recommendation",
    "next steps": "recommendation",
    "recommendation": "recommendation",
    "recommendations": "recommendation",
    "focus areas": "focus_areas",
    "focus area": "focus_areas",
    "metrics": "metrics",
    "results": "metrics",
    "decisions": "decision",
    "decision": "decision",
    "open questions": "open_questions",
    "open question": "open_questions",
}

_KNOWN_LABELS: frozenset[str] = frozenset(_SEMANTIC_MAP.keys())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _semantic_type(label: str) -> str:
    """Return semantic type for *label*, or ``"general"`` if unrecognized."""
    return _SEMANTIC_MAP.get(label.lower().strip(), "general")


def _is_recognized_label(line: str) -> bool:
    """Return True if *line* is a recognized note label.

    A recognized label is a line that ends with ``:`` and whose body
    (before the colon) matches an entry in ``_KNOWN_LABELS``.
    """
    if not line.endswith(":"):
        return False
    candidate = line[:-1].strip().lower()
    return candidate in _KNOWN_LABELS


def _is_bullet(line: str) -> bool:
    """Return True if *line* starts with a common list marker."""
    if not line:
        return False
    if line[0] in "-*•":
        return True
    if len(line) > 2 and line[0].isdigit() and line[1] in ".)":
        return True
    return False


def _strip_bullet(line: str) -> str:
    """Remove leading bullet marker characters and whitespace."""
    return line.lstrip("-*•0123456789.) ").strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(text: str) -> NormalizedNotes:
    """Parse labeled note-style text into a :class:`NormalizedNotes` structure.

    Recognized label-colon headings delimit sections.  Content under each
    label is collected as a list of cleaned string items.  A free-text line
    that appears *before* the first recognized label is treated as the title.

    Bullet markers (``-``, ``*``) are stripped from item text so items are
    plain strings.  Plain (non-bulleted) lines under a label are included
    as-is.

    If no recognized labels are present the returned ``sections`` list is
    empty and ``title`` is ``None`` unless a free-text line was found before
    any label.

    Args:
        text: Raw note text, possibly containing labeled sections.

    Returns:
        A :class:`NormalizedNotes` instance.  Never raises for string input.
    """
    if not text or not text.strip():
        return NormalizedNotes(title=None, sections=[])

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    title: str | None = None
    sections: list[NormalizedSection] = []
    current_label: str | None = None
    current_items: list[str] = []

    for line in lines:
        if _is_recognized_label(line):
            # Flush previous section before starting a new one
            if current_label is not None:
                sections.append(NormalizedSection(
                    label=current_label,
                    semantic_type=_semantic_type(current_label),
                    items=list(current_items),
                ))
            current_label = line[:-1].strip()  # strip trailing ':'
            current_items = []
        elif current_label is None:
            # Before the first recognized label — candidate title
            # Ignore lines that look like unrecognized labels (end with ':')
            if title is None and not line.endswith(":"):
                title = line[:120]
        else:
            # Content line under the current label
            item = _strip_bullet(line) if _is_bullet(line) else line
            if item:
                current_items.append(item)

    # Flush the final section
    if current_label is not None:
        sections.append(NormalizedSection(
            label=current_label,
            semantic_type=_semantic_type(current_label),
            items=list(current_items),
        ))

    return NormalizedNotes(title=title, sections=sections)


def has_labeled_sections(text: str) -> bool:
    """Return ``True`` if *text* contains at least one recognized label line.

    A lightweight check used by extractors to decide whether to delegate to
    the normalizer rather than fall back to keyword heuristics.

    Args:
        text: Raw input text.

    Returns:
        ``True`` when at least one recognized ``Label:`` line is found.
    """
    for line in text.splitlines():
        if _is_recognized_label(line.strip()):
            return True
    return False
