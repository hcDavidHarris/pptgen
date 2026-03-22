"""Rule-based content extractor.

Converts raw text into a :class:`~pptgen.spec.presentation_spec.PresentationSpec`
using simple line-based heuristics.  One extraction strategy exists per
supported playbook identifier.

Design constraints
------------------
- All extraction is deterministic: same input always produces same output.
- Every strategy is guaranteed to return a structurally valid spec even for
  empty or unstructured input (title/subtitle/section title are never empty).
- No regex, no ML, no external dependencies beyond the spec models.
- Strategies are intentionally simple for Stage 2; Stage 3 may refine them.
"""

from __future__ import annotations

from pptgen.spec.presentation_spec import (
    MetricSpec,
    PresentationSpec,
    SectionSpec,
)


# ---------------------------------------------------------------------------
# Low-level line helpers
# ---------------------------------------------------------------------------

def _clean_lines(text: str) -> list[str]:
    """Return stripped, non-empty lines from *text*."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def _is_heading(line: str) -> bool:
    """Return True for standalone heading-style lines.

    A heading is:
    - a short line that ends with ``:`` (nothing after the colon)
    - a line starting with ``#``
    - an ALL-CAPS line with multiple words
    """
    if line.startswith("#"):
        return True
    if line.endswith(":") and len(line) < 60:
        return True
    if line.isupper() and 5 < len(line) < 60 and " " in line:
        return True
    return False


def _is_bullet(line: str) -> bool:
    """Return True if the line looks like a list item."""
    if not line:
        return False
    if line[0] in "-*•":
        return True
    # Numbered list: "1.", "2)", etc.
    if len(line) > 2 and line[0].isdigit() and line[1] in ".)":
        return True
    return False


def _strip_prefix(line: str) -> str:
    """Remove leading list marker characters and whitespace."""
    return line.lstrip("-*•0123456789.) ").strip()


def _lines_under_heading(lines: list[str], *keywords: str) -> list[str]:
    """Return content lines in the section following the first heading that
    contains any of *keywords* (case-insensitive).

    Stops at the next heading so that sections stay scoped.
    """
    inside = False
    result: list[str] = []
    for line in lines:
        lower = line.lower()
        if _is_heading(line):
            if any(kw in lower for kw in keywords):
                inside = True
                continue
            elif inside:
                break
        if inside:
            content = _strip_prefix(line) if _is_bullet(line) else line
            if content:
                result.append(content)
    return result


def _content_bullets(lines: list[str], max_bullets: int = 6) -> list[str]:
    """Collect up to *max_bullets* content lines, preferring bullet items."""
    result: list[str] = []
    for line in lines:
        if _is_heading(line):
            continue
        content = _strip_prefix(line) if _is_bullet(line) else line
        content = content[:120]
        if content:
            result.append(content)
        if len(result) >= max_bullets:
            break
    return result


def _first_title(lines: list[str], fallback: str) -> str:
    """Return the first substantial non-colon-terminated line as a title."""
    for line in lines[:6]:
        candidate = line.rstrip(":").strip()
        if len(candidate) >= 3 and not line.startswith("#"):
            return candidate[:80]
    return fallback


def _try_metric(line: str) -> MetricSpec | None:
    """Attempt to parse ``label: value`` from *line*.

    Returns a :class:`MetricSpec` when the line contains a colon separator,
    the label is 3–40 characters, and the value portion is non-empty.
    """
    if ": " not in line:
        return None
    label, _, value_part = line.partition(": ")
    label = label.strip().rstrip("-*•0123456789.) ")
    value_part = value_part.strip()
    if not (3 <= len(label) <= 40) or not value_part:
        return None
    return MetricSpec(label=label, value=value_part[:40])


# ---------------------------------------------------------------------------
# Per-playbook extraction strategies
# ---------------------------------------------------------------------------

def _extract_meeting_notes(text: str) -> PresentationSpec:
    """Extract a PresentationSpec from meeting-notes input."""
    lines = _clean_lines(text)
    title = _first_title(lines, "Meeting Summary")
    subtitle = "Meeting Notes"

    agenda = _lines_under_heading(lines, "agenda")
    actions = _lines_under_heading(lines, "action item", "action items")
    decisions = _lines_under_heading(lines, "decision", "decisions")
    discussion = _lines_under_heading(lines, "discussion")

    # Fallback: use all content lines when the input is unstructured
    if not any([agenda, actions, decisions, discussion]):
        all_bullets = _content_bullets(lines)
        sections = [SectionSpec(title="Summary", bullets=all_bullets)]
        return PresentationSpec(title=title, subtitle=subtitle, sections=sections)

    sections: list[SectionSpec] = []
    if agenda:
        sections.append(SectionSpec(title="Agenda", bullets=agenda[:6]))
    if discussion:
        sections.append(SectionSpec(title="Discussion", bullets=discussion[:6]))
    if actions:
        sections.append(SectionSpec(title="Action Items", bullets=actions[:6]))
    if decisions:
        sections.append(SectionSpec(title="Decisions", bullets=decisions[:6]))

    if not sections:
        sections = [SectionSpec(title="Summary", bullets=_content_bullets(lines))]

    return PresentationSpec(title=title, subtitle=subtitle, sections=sections)


def _extract_ado_summary(text: str) -> PresentationSpec:
    """Extract a PresentationSpec from an ADO / engineering delivery summary."""
    lines = _clean_lines(text)
    title = "Engineering Delivery Summary"

    # Subtitle: try to pull sprint number/name from first line
    subtitle = lines[0][:60] if lines else "Sprint Update"

    # Delivery content: sprint, velocity, backlog, feature, epic lines
    delivery_keywords = ("sprint", "velocity", "story point", "backlog",
                         "feature", "epic", "work item", "completed", "planned")
    delivery = [
        line for line in lines
        if not _is_heading(line) and any(kw in line.lower() for kw in delivery_keywords)
    ][:6]

    # Blocker content: blocked, blocker, delayed lines
    blocker_keywords = ("blocked", "blocker", "delayed", "dependency",
                        "at risk", "impediment")
    blockers = [
        _strip_prefix(line) if _is_bullet(line) else line
        for line in lines
        if not _is_heading(line) and any(kw in line.lower() for kw in blocker_keywords)
    ][:6]

    sections: list[SectionSpec] = [
        SectionSpec(
            title="Delivery Status",
            bullets=delivery or _content_bullets(lines),
        )
    ]
    if blockers:
        sections.append(SectionSpec(title="Blockers and Risks", bullets=blockers))

    return PresentationSpec(title=title, subtitle=subtitle, sections=sections)


def _extract_architecture_notes(text: str) -> PresentationSpec:
    """Extract a PresentationSpec from architecture / ADR notes."""
    lines = _clean_lines(text)
    title = "Architecture Decision Review"

    # Subtitle: ADR identifier or first line
    subtitle = "Architecture Decision Record"
    for line in lines[:3]:
        if "adr" in line.lower() or "decision" in line.lower():
            subtitle = line.rstrip(":").strip()[:60]
            break

    context = _lines_under_heading(lines, "context", "problem", "background")
    options = _lines_under_heading(
        lines, "option", "options considered", "alternatives"
    )
    decision = _lines_under_heading(lines, "decision record", "decision")
    constraints = _lines_under_heading(
        lines, "constraint", "tradeoff", "trade-off", "consequence"
    )

    sections: list[SectionSpec] = []
    if context:
        sections.append(SectionSpec(title="Context and Problem", bullets=context[:6]))
    if options or decision:
        combined = (options + decision)[:6]
        sections.append(SectionSpec(title="Options and Decision", bullets=combined))
    if constraints:
        sections.append(
            SectionSpec(title="Constraints and Tradeoffs", bullets=constraints[:6])
        )

    if not sections:
        sections = [
            SectionSpec(title="Architecture Overview", bullets=_content_bullets(lines))
        ]

    return PresentationSpec(title=title, subtitle=subtitle, sections=sections)


def _extract_devops_metrics(text: str) -> PresentationSpec:
    """Extract a PresentationSpec from DevOps / DORA metrics content."""
    lines = _clean_lines(text)
    title = "DevOps Scorecard"

    # Subtitle: look for a report title in the first two lines
    subtitle = lines[0][:60] if lines else "DORA Metrics Report"

    # Metric lines: lines that contain ": " and have a recognisable DORA label
    dora_labels = (
        "deployment frequency", "lead time", "mttr", "change failure",
        "mean time", "four key", "throughput", "cycle time",
    )
    metrics: list[MetricSpec] = []
    observation_bullets: list[str] = []
    for line in lines:
        if _is_heading(line):
            continue
        lower = line.lower()
        if any(lbl in lower for lbl in dora_labels):
            m = _try_metric(line)
            if m and len(metrics) < 4:
                metrics.append(m)
                continue
        # Non-metric content lines become bullets
        content = _strip_prefix(line) if _is_bullet(line) else line
        if content and len(observation_bullets) < 6:
            observation_bullets.append(content)

    section = SectionSpec(
        title="Scorecard",
        metrics=metrics,
        bullets=observation_bullets[:6],
    )
    return PresentationSpec(title=title, subtitle=subtitle, sections=[section])


def _extract_generic(text: str) -> PresentationSpec:
    """Extract a minimal PresentationSpec for unclassified content."""
    lines = _clean_lines(text)
    title = _first_title(lines, "Summary") if lines else "Summary"
    subtitle = "Content Overview"

    bullets = _content_bullets(lines)
    sections = [SectionSpec(title="Overview", bullets=bullets)]
    return PresentationSpec(title=title, subtitle=subtitle, sections=sections)


# ---------------------------------------------------------------------------
# Public dispatch
# ---------------------------------------------------------------------------

_EXTRACTORS: dict[str, object] = {
    "meeting-notes-to-eos-rocks": _extract_meeting_notes,
    "ado-summary-to-weekly-delivery": _extract_ado_summary,
    "architecture-notes-to-adr-deck": _extract_architecture_notes,
    "devops-metrics-to-scorecard": _extract_devops_metrics,
    "generic-summary-playbook": _extract_generic,
}


def extract(playbook_id: str, text: str) -> PresentationSpec:
    """Extract a :class:`~pptgen.spec.presentation_spec.PresentationSpec`
    from *text* using the strategy registered for *playbook_id*.

    Falls back to the generic strategy for any unrecognised identifier.
    Always returns a structurally valid spec; never raises for string input.

    Args:
        playbook_id: Playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).
        text:        Raw or pre-normalised input text.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
    """
    strategy = _EXTRACTORS.get(playbook_id, _extract_generic)
    return strategy(text)  # type: ignore[operator]
