"""Phase 5B AI executor integration tests.

Covers:
- default model injection (MockModel used when none supplied)
- custom model injection
- model interface contract enforced at the executor boundary
- fallback path preserved
- deterministic mode unaffected
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.ai.models import LLMModel, MockModel
from pptgen.pipeline import PipelineError, generate_presentation
from pptgen.playbook_engine.ai_executor import _build_prompt, _parse_spec, run
from pptgen.spec.presentation_spec import PresentationSpec


_MEETING = "Meeting notes. Attendees: Alice. Action items: review deliverables."
_ADO = "Sprint 12. Velocity 38 story points. Three blocked."


# ---------------------------------------------------------------------------
# Default model injection
# ---------------------------------------------------------------------------

class TestDefaultModelInjection:
    def test_run_without_model_returns_spec(self):
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        assert isinstance(spec, PresentationSpec)

    def test_run_without_model_uses_mock(self):
        """Subtitle should carry the (AI) label from MockModel."""
        spec = run("meeting-notes-to-eos-rocks", _MEETING)
        assert "(AI)" in spec.subtitle

    def test_run_without_model_is_deterministic(self):
        results = [run("meeting-notes-to-eos-rocks", _MEETING) for _ in range(3)]
        titles = {r.title for r in results}
        assert len(titles) == 1


# ---------------------------------------------------------------------------
# Custom model injection
# ---------------------------------------------------------------------------

class TestCustomModelInjection:
    def test_run_accepts_injected_model(self):
        model = MockModel()
        spec = run("meeting-notes-to-eos-rocks", _MEETING, model=model)
        assert isinstance(spec, PresentationSpec)

    def test_injected_model_output_used(self):
        """A custom model that always returns a fixed dict should be used."""
        class FixedModel:
            def generate(self, prompt: str) -> dict:
                return {
                    "title": "Custom Title",
                    "subtitle": "Custom Subtitle",
                    "sections": [{"title": "Fixed", "bullets": ["point a"]}],
                }

        assert isinstance(FixedModel(), LLMModel)
        spec = run("generic-summary-playbook", "any text", model=FixedModel())
        assert spec.title == "Custom Title"
        assert spec.subtitle == "Custom Subtitle"
        assert spec.sections[0].title == "Fixed"

    def test_injected_model_generate_receives_prompt_string(self):
        """model.generate() must be called with a non-empty prompt string."""
        received: list[str] = []

        class CapturingModel:
            def generate(self, prompt: str) -> dict:
                received.append(prompt)
                return {
                    "title": "T",
                    "subtitle": "S",
                    "sections": [{"title": "S1", "bullets": ["b"]}],
                }

        run("meeting-notes-to-eos-rocks", _MEETING, model=CapturingModel())
        assert len(received) == 1
        assert isinstance(received[0], str)
        assert received[0]  # non-empty

    def test_injected_model_prompt_contains_playbook_id(self):
        received: list[str] = []

        class CapturingModel:
            def generate(self, prompt: str) -> dict:
                received.append(prompt)
                return MockModel().generate(prompt)

        run("ado-summary-to-weekly-delivery", _ADO, model=CapturingModel())
        assert "ado-summary-to-weekly-delivery" in received[0]

    def test_injected_model_prompt_contains_input_text(self):
        received: list[str] = []

        class CapturingModel:
            def generate(self, prompt: str) -> dict:
                received.append(prompt)
                return MockModel().generate(prompt)

        run("meeting-notes-to-eos-rocks", "unique_marker_xyz", model=CapturingModel())
        assert "unique_marker_xyz" in received[0]


# ---------------------------------------------------------------------------
# Fallback path preserved
# ---------------------------------------------------------------------------

class TestFallbackPreserved:
    def test_model_that_raises_propagates_error(self):
        """ai_executor should NOT swallow model errors — engine.py handles fallback."""
        class BrokenModel:
            def generate(self, prompt: str) -> dict:
                raise RuntimeError("simulated model failure")

        with pytest.raises(RuntimeError, match="simulated model failure"):
            run("generic-summary-playbook", "text", model=BrokenModel())

    def test_model_returning_empty_dict_gets_fallbacks(self):
        """_parse_spec() must supply sensible fallbacks for missing fields."""
        class EmptyModel:
            def generate(self, prompt: str) -> dict:
                return {}

        spec = run("generic-summary-playbook", "text", model=EmptyModel())
        assert spec.title == "AI Presentation"
        assert spec.subtitle == "AI-assisted generation"
        assert len(spec.sections) >= 1

    def test_pipeline_ai_fallback_still_works(self, tmp_path):
        """Full pipeline with AI mode should still render successfully."""
        out = tmp_path / "out.pptx"
        result = generate_presentation(_MEETING, output_path=out, mode="ai")
        assert result.stage == "rendered"
        assert out.exists()


# ---------------------------------------------------------------------------
# Deterministic mode unaffected
# ---------------------------------------------------------------------------

class TestDeterministicModeUnaffected:
    def test_deterministic_mode_still_works(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(_MEETING, output_path=out, mode="deterministic")
        assert result.stage == "rendered"
        assert out.exists()

    def test_deterministic_mode_is_default(self, tmp_path):
        out = tmp_path / "out.pptx"
        result = generate_presentation(_MEETING, output_path=out)
        assert result.mode == "deterministic"
        assert result.stage == "rendered"

    def test_deterministic_mode_does_not_carry_ai_label(self):
        result = generate_presentation(_MEETING)
        assert "(AI)" not in (result.presentation_spec.subtitle or "")
