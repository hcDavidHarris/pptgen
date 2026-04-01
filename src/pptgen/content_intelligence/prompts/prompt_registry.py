"""Prompt registry — Phase 11B single source of truth.

All prompt access must go through this module.  Prompt text lives in the
individual prompt modules (narrative_prompt, expansion_prompt, insight_prompt).
This registry maps names to builder functions and provides a unified API.

Usage::

    from pptgen.content_intelligence.prompts.prompt_registry import get_prompt
    prompt = get_prompt("narrative", {"topic": "Cloud Migration", ...})

Or via the named helpers::

    from pptgen.content_intelligence.prompts.prompt_registry import (
        get_narrative_prompt,
        get_expansion_prompt,
        get_insight_prompt,
    )
"""
from __future__ import annotations

from typing import Callable

from . import expansion_prompt, insight_prompt, narrative_prompt

# Stable name constants — use these instead of bare strings.
NARRATIVE: str = "narrative"
EXPANSION: str = "expansion"
INSIGHT: str = "insight"

# Internal dispatch table — one entry per prompt.
_REGISTRY: dict[str, Callable[[dict], str]] = {
    NARRATIVE: narrative_prompt.build_prompt,
    EXPANSION: expansion_prompt.build_prompt,
    INSIGHT: insight_prompt.build_prompt,
}


def get_prompt(prompt_name: str, context: dict) -> str:
    """Return the rendered prompt string for *prompt_name* with *context*.

    Args:
        prompt_name: One of ``NARRATIVE``, ``EXPANSION``, ``INSIGHT``.
        context: Dict of template variables for the chosen prompt.

    Returns:
        Rendered prompt string.

    Raises:
        KeyError: If *prompt_name* is not registered.
    """
    builder = _REGISTRY.get(prompt_name)
    if builder is None:
        raise KeyError(
            f"Unknown prompt name: {prompt_name!r}. "
            f"Valid names: {sorted(_REGISTRY)}"
        )
    return builder(context)


def get_narrative_prompt(context: dict) -> str:
    """Return the rendered narrative prompt for *context*."""
    return narrative_prompt.build_prompt(context)


def get_expansion_prompt(context: dict) -> str:
    """Return the rendered expansion prompt for *context*."""
    return expansion_prompt.build_prompt(context)


def get_insight_prompt(context: dict) -> str:
    """Return the rendered insight prompt for *context*."""
    return insight_prompt.build_prompt(context)
