"""Model factory helpers.

Provides a single resolution point so callers never need to import
:class:`MockModel` directly when they only want the current default.
"""

from __future__ import annotations

from .llm_interface import LLMModel
from .mock_model import MockModel


def get_default_model() -> LLMModel:
    """Return the default :class:`LLMModel` instance.

    Currently returns a :class:`MockModel`.  Phase 5C will extend this to
    inspect environment variables (e.g. ``PPTGEN_MODEL_PROVIDER``) and
    return the appropriate provider adapter.

    Returns:
        A ready-to-use :class:`LLMModel` instance.
    """
    return MockModel()
