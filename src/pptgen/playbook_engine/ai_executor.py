"""AI playbook executor.

Provides the AI execution path that returns a valid
:class:`~pptgen.spec.presentation_spec.PresentationSpec` by delegating
content generation to an :class:`~pptgen.ai.models.LLMModel`.

Phase 5B changes
----------------
The internal ``_mock_llm_call()`` function has been removed.  Generation
is now delegated to the injected *model* argument (default:
:class:`~pptgen.ai.models.MockModel`).  The structural seam is identical:
prompt construction and response parsing are unchanged so the returned
:class:`~pptgen.spec.presentation_spec.PresentationSpec` is identical to
the Phase 5A output.

Fallback
--------
If model generation or response parsing raises, the caller (``engine.py``)
is responsible for deciding whether to fall back to the deterministic
executor.  This module does *not* swallow errors silently.
"""

from __future__ import annotations

from ..ai.models import LLMModel, get_default_model
from ..spec.presentation_spec import PresentationSpec, SectionSpec


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    playbook_id: str,
    input_text: str,
    model: LLMModel | None = None,
) -> PresentationSpec:
    """Execute the AI-assisted generation path for *playbook_id*.

    Builds a prompt from the playbook context and input text, calls
    *model* (falling back to the default :class:`~pptgen.ai.models.MockModel`
    when ``None``), and parses the response into a
    :class:`~pptgen.spec.presentation_spec.PresentationSpec`.

    Args:
        playbook_id: Playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).
        input_text:  Normalised text to generate content from.
        model:       :class:`~pptgen.ai.models.LLMModel` instance to use.
                     If ``None``, the default model (currently
                     :class:`~pptgen.ai.models.MockModel`) is used.

    Returns:
        A valid :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
    """
    if model is None:
        model = get_default_model()

    prompt = _build_prompt(playbook_id, input_text)
    raw = model.generate(prompt)
    return _parse_spec(raw)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_prompt(playbook_id: str, input_text: str) -> str:
    """Return a structured prompt string for the given playbook and input.

    The prompt format is understood by :class:`~pptgen.ai.models.MockModel`
    and documented for future real provider adapters.
    """
    return (
        f"[pptgen] playbook={playbook_id}\n"
        f"[task] Extract key presentation points from the following input and "
        f"structure them as title, subtitle, and sections with bullet points.\n"
        f"[input]\n{input_text or '(empty)'}\n"
    )


# ---------------------------------------------------------------------------
# Bullet synthesis helper  (used by MockModel; kept here for test coverage)
# ---------------------------------------------------------------------------

def _synthesize_bullets(lines: list[str], max_bullets: int = 6) -> list[str]:
    """Convert a list of text lines into compact bullet strings.

    Strips common list prefixes (``-``, ``*``, ``•``, ``N.``), deduplicates,
    and returns at most *max_bullets* items.  If no content lines exist,
    returns a single fallback bullet.

    This helper is retained in the executor module so that existing tests
    that import it directly continue to work.
    """
    bullets: list[str] = []
    seen: set[str] = set()

    for line in lines:
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
    """Convert *raw* dict (as returned by the model) to a PresentationSpec.

    Args:
        raw: Dict with keys ``title``, ``subtitle``, and ``sections``
             (each section has ``title`` and ``bullets``).

    Returns:
        A validated :class:`~pptgen.spec.presentation_spec.PresentationSpec`.
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
