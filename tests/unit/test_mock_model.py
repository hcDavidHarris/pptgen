"""Unit tests for MockModel."""

from __future__ import annotations

from pptgen.ai.models import MockModel, get_default_model
from pptgen.playbook_engine.ai_executor import _build_prompt


_MEETING_PROMPT = _build_prompt(
    "meeting-notes-to-eos-rocks",
    "Meeting notes. Attendees: Alice, Bob. Action items: review deliverables.",
)
_ADO_PROMPT = _build_prompt(
    "ado-summary-to-weekly-delivery",
    "Sprint 12. Velocity 38 story points. Three blocked.",
)
_EMPTY_PROMPT = _build_prompt("generic-summary-playbook", "")


class TestMockModelBasics:
    def test_instantiation(self):
        assert MockModel() is not None

    def test_generate_returns_dict(self):
        result = MockModel().generate(_MEETING_PROMPT)
        assert isinstance(result, dict)

    def test_result_has_title(self):
        result = MockModel().generate(_MEETING_PROMPT)
        assert "title" in result
        assert result["title"]

    def test_result_has_subtitle(self):
        result = MockModel().generate(_MEETING_PROMPT)
        assert "subtitle" in result
        assert result["subtitle"]

    def test_result_has_sections(self):
        result = MockModel().generate(_MEETING_PROMPT)
        assert "sections" in result
        assert isinstance(result["sections"], list)
        assert len(result["sections"]) >= 1

    def test_subtitle_contains_ai_label(self):
        result = MockModel().generate(_MEETING_PROMPT)
        assert "(AI)" in result["subtitle"]

    def test_section_has_title_and_bullets(self):
        result = MockModel().generate(_MEETING_PROMPT)
        sec = result["sections"][0]
        assert "title" in sec
        assert "bullets" in sec
        assert isinstance(sec["bullets"], list)


class TestMockModelDeterminism:
    def test_same_prompt_same_title(self):
        model = MockModel()
        titles = {model.generate(_MEETING_PROMPT)["title"] for _ in range(5)}
        assert len(titles) == 1

    def test_same_prompt_same_section_count(self):
        model = MockModel()
        counts = {len(model.generate(_ADO_PROMPT)["sections"]) for _ in range(3)}
        assert len(counts) == 1

    def test_different_prompts_different_subtitles(self):
        model = MockModel()
        sub_meeting = model.generate(_MEETING_PROMPT)["subtitle"]
        sub_ado = model.generate(_ADO_PROMPT)["subtitle"]
        assert sub_meeting != sub_ado


class TestMockModelEmptyInput:
    def test_empty_input_returns_valid_dict(self):
        result = MockModel().generate(_EMPTY_PROMPT)
        assert isinstance(result, dict)

    def test_empty_input_title_falls_back(self):
        result = MockModel().generate(_EMPTY_PROMPT)
        assert result["title"]

    def test_empty_input_has_at_least_one_section(self):
        result = MockModel().generate(_EMPTY_PROMPT)
        assert len(result["sections"]) >= 1

    def test_empty_input_bullets_fallback(self):
        result = MockModel().generate(_EMPTY_PROMPT)
        bullets = result["sections"][0]["bullets"]
        assert bullets == ["(no content)"]


class TestMockModelAllPlaybooks:
    def test_all_known_playbooks_produce_valid_dict(self):
        playbooks = [
            ("meeting-notes-to-eos-rocks", "meeting notes with action items"),
            ("ado-summary-to-weekly-delivery", "sprint velocity 42 story points"),
            ("architecture-notes-to-adr-deck", "ADR-007 decision event-driven"),
            ("devops-metrics-to-scorecard", "DORA deployment frequency 4/day"),
            ("generic-summary-playbook", "general quarterly update"),
        ]
        model = MockModel()
        for pid, text in playbooks:
            prompt = _build_prompt(pid, text)
            result = model.generate(prompt)
            assert result["title"]
            assert result["subtitle"]
            assert result["sections"]


class TestGetDefaultModel:
    def test_returns_mock_model(self):
        model = get_default_model()
        assert isinstance(model, MockModel)

    def test_default_model_generate_works(self):
        model = get_default_model()
        result = model.generate(_MEETING_PROMPT)
        assert isinstance(result, dict)
