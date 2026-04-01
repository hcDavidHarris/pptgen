"""Ollama model adapter stub.

Phase 5C will implement this using the Ollama REST API (``http://localhost:11434``).

Usage (future)::

    from pptgen.ai.models.ollama_model import OllamaModel
    model = OllamaModel(model="llama3")
    spec = ai_executor.run(playbook_id, text, model=model)
"""

from __future__ import annotations


class OllamaModel:
    """Placeholder adapter for the Ollama local inference server.

    Not yet implemented.  Instantiating and calling ``generate()`` raises
    :exc:`NotImplementedError` until Phase 5C.

    Args:
        model: Ollama model name (e.g. ``"llama3"``, ``"mistral"``).
        base_url: Base URL of the Ollama server.
                  Defaults to ``"http://localhost:11434"``.
    """

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str) -> dict:  # noqa: ARG002
        """Not implemented — requires Phase 5C."""
        raise NotImplementedError(
            "OllamaModel is not yet implemented.  "
            "Use MockModel for local development or wait for Phase 5C."
        )
