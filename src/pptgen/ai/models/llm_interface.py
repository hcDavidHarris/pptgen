"""Vendor-neutral LLM model interface.

All model implementations (mock, OpenAI, Anthropic, Ollama, …) must
satisfy this interface so the AI executor can use them interchangeably.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMModel(Protocol):
    """Structural interface for a language model callable.

    Any object that provides a ``generate(prompt)`` method returning a
    ``dict`` qualifies as an :class:`LLMModel` — no explicit inheritance
    required.

    Contract
    --------
    - ``generate`` must accept a single ``str`` prompt.
    - ``generate`` must return a ``dict`` with at minimum the keys
      ``"title"``, ``"subtitle"``, and ``"sections"``.  The AI executor
      passes the returned dict directly to its ``_parse_spec()`` helper,
      which supplies sensible fallbacks for any missing or empty values.
    - ``generate`` must be synchronous.
    - ``generate`` must not make destructive side-effects visible outside
      the model instance.
    """

    def generate(self, prompt: str) -> dict:
        """Generate a structured presentation spec from *prompt*.

        Args:
            prompt: The full prompt string built by the AI executor.

        Returns:
            A ``dict`` containing at minimum ``"title"``, ``"subtitle"``,
            and ``"sections"`` keys, matching the shape expected by
            :func:`pptgen.playbook_engine.ai_executor._parse_spec`.
        """
        ...  # pragma: no cover
