"""Model abstraction layer for pptgen AI execution.

Public surface::

    from pptgen.ai.models import LLMModel, MockModel, get_default_model
"""

from .llm_interface import LLMModel
from .mock_model import MockModel
from .model_factory import get_default_model

__all__ = ["LLMModel", "MockModel", "get_default_model"]
