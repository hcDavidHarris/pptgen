"""Deterministic mock LLM model.

Used as the default model for AI execution when no real provider is
configured.  Produces structurally valid, fully deterministic output so
that AI-mode tests can run without any network access or API keys.

This was previously the ``_mock_llm_call()`` function inside
``ai_executor.py``; it is now a proper :class:`LLMModel` implementation.
"""

from __future__ import annotations

import re


# Mapping from playbook ID to a human-readable label used in subtitles.
_PLAYBOOK_LABELS: dict[str, str] = {
    "meeting-notes-to-eos-rocks": "Meeting Summary",
    "ado-summary-to-weekly-delivery": "Sprint Delivery Brief",
    "architecture-notes-to-adr-deck": "Architecture Overview",
    "devops-metrics-to-scorecard": "DevOps Performance Brief",
    "generic-summary-playbook": "Executive Summary",
}

# Regex that strips common list-prefix characters before a bullet body.
_LIST_PREFIX = re.compile(r"^[-*•\d.]+\s*")


class MockModel:
    """Deterministic mock implementation of :class:`~pptgen.ai.models.LLMModel`.

    Parses the pptgen-style prompt produced by the AI executor and
    synthesises a structured dict without any external calls.

    Behaviour
    ---------
    - Title  : first non-empty line of the ``[input]`` block, or the
               playbook label if the input is empty.
    - Subtitle: ``"<label> (AI)"``.
    - Sections: one ``"Key Points"`` section (up to 6 bullets); a second
                ``"Context & Notes"`` section if the input has more than
                6 content lines.
    """

    def generate(self, prompt: str) -> dict:
        """Return a structured presentation dict derived from *prompt*.

        The prompt is expected to follow the format produced by
        :func:`pptgen.playbook_engine.ai_executor._build_prompt`.

        Args:
            prompt: Full prompt string containing ``[pptgen]``,
                    ``[task]``, and ``[input]`` sections.

        Returns:
            ``dict`` with keys ``"title"``, ``"subtitle"``, and
            ``"sections"``.
        """
        playbook_id, input_text = _parse_prompt(prompt)
        return _synthesise_response(playbook_id, input_text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_prompt(prompt: str) -> tuple[str, str]:
    """Extract playbook_id and input_text from a pptgen prompt string."""
    playbook_id = ""
    input_text = ""

    for line in prompt.splitlines():
        if line.startswith("[pptgen]"):
            # e.g. "[pptgen] playbook=meeting-notes-to-eos-rocks"
            _, _, rest = line.partition("playbook=")
            playbook_id = rest.strip()
        elif line == "[input]":
            # Everything after [input] is the raw input text
            idx = prompt.index("[input]")
            input_text = prompt[idx + len("[input]"):].strip()
            # Remove the "(empty)" sentinel if present
            if input_text == "(empty)":
                input_text = ""
            break

    return playbook_id, input_text


def _synthesise_response(playbook_id: str, input_text: str) -> dict:
    """Build the structured mock response dict."""
    label = _PLAYBOOK_LABELS.get(playbook_id, "Presentation")
    lines = [ln.strip() for ln in input_text.splitlines() if ln.strip()]

    title = lines[0] if lines else label
    subtitle = f"{label} (AI)"
    key_bullets = _synthesise_bullets(lines)

    sections: list[dict] = [{"title": "Key Points", "bullets": key_bullets}]

    if len(lines) > 6:
        context_bullets = _synthesise_bullets(lines[6:], max_bullets=4)
        sections.append({"title": "Context & Notes", "bullets": context_bullets})

    return {"title": title, "subtitle": subtitle, "sections": sections}


def _synthesise_bullets(lines: list[str], max_bullets: int = 6) -> list[str]:
    """Convert text lines to deduplicated bullet strings."""
    bullets: list[str] = []
    seen: set[str] = set()

    for line in lines:
        stripped = _LIST_PREFIX.sub("", line).strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        bullets.append(stripped)
        if len(bullets) >= max_bullets:
            break

    return bullets if bullets else ["(no content)"]
