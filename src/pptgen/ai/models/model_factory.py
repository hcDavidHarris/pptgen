"""Model factory helpers.

Provides a single resolution point so callers never need to import
:class:`MockModel` directly when they only want the current default.
"""

from __future__ import annotations

from ...config import get_settings
from .llm_interface import LLMModel
from .mock_model import MockModel


def get_default_model() -> LLMModel:
    """Return the :class:`LLMModel` instance for the configured provider.

    Reads ``PPTGEN_MODEL_PROVIDER`` from settings (via :func:`get_settings`)
    to select the provider adapter.  Currently only ``"mock"`` is implemented;
    additional providers (``"anthropic"``, ``"openai"``, ``"ollama"``) will
    be added when their adapters are introduced.

    Returns:
        A ready-to-use :class:`LLMModel` instance.
    """
    settings = get_settings()
    provider = settings.model_provider

    if provider == "mock":
        return MockModel()

    # Placeholder: non-mock providers are not yet implemented.
    # Return MockModel as a safe fallback until adapters are added.
    return MockModel()
