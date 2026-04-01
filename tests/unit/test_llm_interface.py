"""Unit tests for the LLM model interface."""

from __future__ import annotations

import pytest

from pptgen.ai.models import LLMModel, MockModel
from pptgen.ai.models.anthropic_model import AnthropicModel
from pptgen.ai.models.ollama_model import OllamaModel
from pptgen.ai.models.openai_model import OpenAIModel


class TestLLMModelProtocol:
    def test_protocol_is_importable(self):
        assert LLMModel is not None

    def test_mock_model_satisfies_protocol(self):
        assert isinstance(MockModel(), LLMModel)

    def test_protocol_requires_generate_method(self):
        class BadModel:
            pass

        assert not isinstance(BadModel(), LLMModel)

    def test_object_with_generate_satisfies_protocol(self):
        class MinimalModel:
            def generate(self, prompt: str) -> dict:
                return {"title": "T", "subtitle": "S", "sections": []}

        assert isinstance(MinimalModel(), LLMModel)

    def test_generate_signature_accepts_string(self):
        model = MockModel()
        result = model.generate("some prompt text")
        assert isinstance(result, dict)


class TestProviderStubsSatisfyProtocol:
    """Provider stubs should be importable and structurally correct."""

    def test_openai_model_importable(self):
        model = OpenAIModel()
        assert model is not None

    def test_anthropic_model_importable(self):
        model = AnthropicModel()
        assert model is not None

    def test_ollama_model_importable(self):
        model = OllamaModel()
        assert model is not None

    def test_openai_has_generate_method(self):
        assert callable(OpenAIModel().generate)

    def test_anthropic_has_generate_method(self):
        assert callable(AnthropicModel().generate)

    def test_ollama_has_generate_method(self):
        assert callable(OllamaModel().generate)

    def test_openai_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            OpenAIModel().generate("test")

    def test_anthropic_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            AnthropicModel().generate("test")

    def test_ollama_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            OllamaModel().generate("test")
