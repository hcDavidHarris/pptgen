"""AI playbook executor.

Provides a mockable AI execution path that returns a valid
:class:`~pptgen.spec.presentation_spec.PresentationSpec`.

Phase 5A status
---------------
This module is a clean **seam** for future real LLM integration (Phase 5B).
Currently it uses a fully deterministic mock generator so that:

- the execution path is structurally identical to the real integration,
- tests can run without external API calls,
- the spec returned is structurally different from the deterministic extractor
  (different section naming, compact bullet synthesis) so the two strategies
  are distinguishable in tests.

Phase 5B will replace ``_mock_llm_call()`` with a real model provider call.
No other function in this module needs to change.

Fallback
--------
If the mock/real generation step raises, the caller (``engine.py``) is
responsible for deciding whether to fall back to the deterministic executor.
This module does *not* swallow errors silently.
"""

from __future__ import annotations

from ..spec.presentation_spec import PresentationSpec, SectionSpec


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(playbook_id: str, input_text: str) -> PresentationSpec:
    """Execute the AI-assisted generation path for *playbook_id*.

    Builds a prompt from the playbook context and input text, calls the
    (currently mocked) LLM, and parses the response into a
    :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Args:
        playbook_id: Playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).
        input_text:  Normalised text to generate content from.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
    """
    prompt = _build_prompt(playbook_id, input_text)
    raw = _mock_llm_call(prompt, playbook_id, input_text)
    return _parse_spec(raw)


# ---------------------------------------------------------------------------
# Prompt construction  (seam for Phase 5B)
# ---------------------------------------------------------------------------

def _build_prompt(playbook_id: str, input_text: str) -> str:
    """Return a structured prompt string for the given playbook and input.

    In Phase 5B this will produce the full system+user prompt sent to the
    model.  Today it simply records the intent for observability.
    """
    return (
        f"[pptgen] playbook={playbook_id}\n"
        f"[task] Extract key presentation points from the following input and "
        f"structure them as title, subtitle, and sections with bullet points.\n"
        f"[input]\n{input_text or '(empty)'}\n"
    )


# ---------------------------------------------------------------------------
# Mock LLM call  (replace with real provider in Phase 5B)
# ---------------------------------------------------------------------------

_PLAYBOOK_LABELS: dict[str, str] = {
    "meeting-notes-to-eos-rocks": "Meeting Summary",
    "ado-summary-to-weekly-delivery": "Sprint Delivery Brief",
    "architecture-notes-to-adr-deck": "Architecture Overview",
    "devops-metrics-to-scorecard": "DevOps Performance Brief",
    "generic-summary-playbook": "Executive Summary",
}


def _mock_llm_call(
    prompt: str,  # noqa: ARG001 — consumed by real model in Phase 5B
    playbook_id: str,
    input_text: str,
) -> dict:
    """Simulate an LLM response by applying simple text synthesis.

    Returns a plain dict with keys ``title``, ``subtitle``, and ``sections``.
    Each section has ``title`` and ``bullets`` keys.

    This function is deterministic: the same *playbook_id* and *input_text*
    always produce the same output.  Phase 5B will replace this body with a
    real model API call.
    """
    label = _PLAYBOOK_LABELS.get(playbook_id, "Presentation")
    lines = [ln.strip() for ln in input_text.splitlines() if ln.strip()]

    # Title: first line of input, or label fallback
    title = lines[0] if lines else label

    # Subtitle: playbook label + " (AI)"
    subtitle = f"{label} (AI)"

    # Key points: up to 6 non-heading content lines synthesized into bullets
    key_bullets = _synthesize_bullets(lines)

    # Sections: one "Key Points" section always present
    sections: list[dict] = [
        {"title": "Key Points", "bullets": key_bullets},
    ]

    # If input is rich enough, add a "Context & Notes" section
    if len(lines) > 6:
        context_bullets = _synthesize_bullets(lines[6:], max_bullets=4)
        sections.append({"title": "Context & Notes", "bullets": context_bullets})

    return {
        "title": title,
        "subtitle": subtitle,
        "sections": sections,
    }


def _synthesize_bullets(lines: list[str], max_bullets: int = 6) -> list[str]:
    """Convert a list of text lines into compact bullet strings.

    Strips common list prefixes (``-``, ``*``, ``•``, ``N.``), deduplicates,
    and returns at most *max_bullets* items.  If no content lines exist,
    returns a single fallback bullet.
    """
    bullets: list[str] = []
    seen: set[str] = set()

    for line in lines:
        # Strip list-prefix characters
        stripped = line.lstrip("-*•0123456789. \t")
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        bullets.append(stripped)
        if len(bullets) >= max_bullets:
            break

    return bullets if bullets else ["(no content)"]


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_spec(raw: dict) -> PresentationSpec:
    """Convert *raw* dict (as returned by the mock/real LLM) to a PresentationSpec.

    Args:
        raw: Dict with keys ``title``, ``subtitle``, and ``sections``
             (each section has ``title`` and ``bullets``).

    Returns:
        A validated :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Raises:
        ValueError: If a required field is missing or empty after normalisation.
    """
    title = str(raw.get("title") or "").strip() or "AI Presentation"
    subtitle = str(raw.get("subtitle") or "").strip() or "AI-assisted generation"

    sections: list[SectionSpec] = []
    for sec in raw.get("sections") or []:
        sec_title = str(sec.get("title") or "").strip()
        bullets: list[str] = [str(b).strip() for b in sec.get("bullets") or [] if str(b).strip()]
        if not sec_title:
            continue
        sections.append(SectionSpec(title=sec_title, bullets=bullets))

    if not sections:
        sections = [SectionSpec(title="Overview", bullets=["(no content extracted)"])]

    return PresentationSpec(title=title, subtitle=subtitle, sections=sections)
