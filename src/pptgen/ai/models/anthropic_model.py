"""Anthropic model adapter stub.

Phase 5C will implement this using the ``anthropic`` SDK.

Usage (future)::

    from pptgen.ai.models.anthropic_model import AnthropicModel
    model = AnthropicModel(api_key="...", model="claude-sonnet-4-6")
    spec = ai_executor.run(playbook_id, text, model=model)
"""

from __future__ import annotations


class AnthropicModel:
    """Placeholder adapter for the Anthropic Messages API.

    Not yet implemented.  Instantiating and calling ``generate()`` raises
    :exc:`NotImplementedError` until Phase 5C.

    Args:
        model: Anthropic model ID (e.g. ``"claude-sonnet-4-6"``).
        api_key: Anthropic API key.  If omitted the adapter will look for
                 the ``ANTHROPIC_API_KEY`` environment variable in Phase 5C.
    """

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key

    def generate(self, prompt: str) -> dict:  # noqa: ARG002
        """Not implemented — requires Phase 5C."""
        raise NotImplementedError(
            "AnthropicModel is not yet implemented.  "
            "Use MockModel for local development or wait for Phase 5C."
        )
