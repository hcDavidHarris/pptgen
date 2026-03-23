"""OpenAI model adapter stub.

Phase 5C will implement this using the ``openai`` SDK.

Usage (future)::

    from pptgen.ai.models.openai_model import OpenAIModel
    model = OpenAIModel(api_key="...", model="gpt-4o")
    spec = ai_executor.run(playbook_id, text, model=model)
"""

from __future__ import annotations


class OpenAIModel:
    """Placeholder adapter for the OpenAI Chat Completions API.

    Not yet implemented.  Instantiating and calling ``generate()`` raises
    :exc:`NotImplementedError` until Phase 5C.

    Args:
        model: OpenAI model name (e.g. ``"gpt-4o"``).
        api_key: OpenAI API key.  If omitted the adapter will look for
                 the ``OPENAI_API_KEY`` environment variable in Phase 5C.
    """

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        self.model = model
        self.api_key = api_key

    def generate(self, prompt: str) -> dict:  # noqa: ARG002
        """Not implemented — requires Phase 5C."""
        raise NotImplementedError(
            "OpenAIModel is not yet implemented.  "
            "Use MockModel for local development or wait for Phase 5C."
        )
