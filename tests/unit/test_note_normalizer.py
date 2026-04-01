"""Unit tests for the note normalizer utility."""
from __future__ import annotations

import pytest

from pptgen.playbook_engine.note_normalizer import (
    NormalizedNotes,
    NormalizedSection,
    has_labeled_sections,
    normalize,
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

_LABELED_TEXT = """\
Sprint 14 Review Notes

Problems:
- retention only runs on shutdown
- UI visibility weak
- run metrics not exposed

Next Step:
Phase 6D Observability

Focus Areas:
- telemetry
- run metrics
- CLI inspection
"""


class TestNormalizeBasic:
    def test_returns_normalized_notes_instance(self):
        result = normalize(_LABELED_TEXT)
        assert isinstance(result, NormalizedNotes)

    def test_empty_string_returns_empty_result(self):
        result = normalize("")
        assert result.title is None
        assert result.sections == []

    def test_whitespace_only_returns_empty_result(self):
        result = normalize("   \n\n  ")
        assert result.title is None
        assert result.sections == []

    def test_no_labels_returns_empty_sections(self):
        result = normalize("Just some text\nwith no labels here")
        assert result.sections == []

    def test_no_labels_still_extracts_title(self):
        result = normalize("Just some text\nwith no labels here")
        assert result.title == "Just some text"


class TestTitleExtraction:
    def test_title_from_line_before_first_label(self):
        result = normalize(_LABELED_TEXT)
        assert result.title == "Sprint 14 Review Notes"

    def test_title_none_when_input_starts_with_label(self):
        text = "Problems:\n- something went wrong\n"
        result = normalize(text)
        assert result.title is None

    def test_title_ignores_unrecognized_label_lines(self):
        text = "Preamble:\n- some item\n\nProblems:\n- issue\n"
        # "Preamble:" is not a recognized label, so it won't start a section,
        # but since it ends with ':', it also won't become the title
        result = normalize(text)
        assert result.title is None or "Preamble" not in (result.title or "")

    def test_title_truncated_at_120_chars(self):
        long_title = "A" * 200
        text = long_title + "\n\nProblems:\n- x\n"
        result = normalize(text)
        assert result.title is not None
        assert len(result.title) <= 120


class TestSectionParsing:
    def test_three_sections_from_labeled_text(self):
        result = normalize(_LABELED_TEXT)
        assert len(result.sections) == 3

    def test_section_labels_preserved(self):
        result = normalize(_LABELED_TEXT)
        labels = [s.label for s in result.sections]
        assert "Problems" in labels
        assert "Next Step" in labels
        assert "Focus Areas" in labels

    def test_section_items_populated(self):
        result = normalize(_LABELED_TEXT)
        problems = next(s for s in result.sections if s.label == "Problems")
        assert len(problems.items) == 3

    def test_plain_line_under_label_included(self):
        result = normalize(_LABELED_TEXT)
        next_step = next(s for s in result.sections if s.label == "Next Step")
        assert "Phase 6D Observability" in next_step.items

    def test_empty_section_still_created(self):
        text = "Problems:\n\nNext Step:\n- do something\n"
        result = normalize(text)
        labels = [s.label for s in result.sections]
        assert "Problems" in labels
        problems = next(s for s in result.sections if s.label == "Problems")
        assert problems.items == []


class TestBulletParsing:
    def test_dash_bullets_stripped(self):
        text = "Problems:\n- first issue\n- second issue\n"
        result = normalize(text)
        items = result.sections[0].items
        assert "first issue" in items
        assert "-" not in items[0]

    def test_star_bullets_stripped(self):
        text = "Focus Areas:\n* telemetry\n* metrics\n"
        result = normalize(text)
        items = result.sections[0].items
        assert "telemetry" in items
        assert "*" not in items[0]

    def test_plain_lines_not_mangled(self):
        text = "Next Step:\nPhase 6D Observability\n"
        result = normalize(text)
        assert result.sections[0].items == ["Phase 6D Observability"]

    def test_mixed_bullet_and_plain_lines(self):
        text = "Focus Areas:\n- telemetry\nrun metrics\n* CLI inspection\n"
        result = normalize(text)
        items = result.sections[0].items
        assert "telemetry" in items
        assert "run metrics" in items
        assert "CLI inspection" in items


class TestCaseInsensitivity:
    def test_lowercase_label_recognized(self):
        text = "problems:\n- x\n"
        result = normalize(text)
        assert len(result.sections) == 1

    def test_uppercase_label_recognized(self):
        text = "PROBLEMS:\n- x\n"
        result = normalize(text)
        # "PROBLEMS" is all-caps; normalize lowercases for lookup
        # The _is_recognized_label checks candidate.lower()
        assert len(result.sections) == 1

    def test_mixed_case_label_recognized(self):
        text = "Next Steps:\n- do it\n"
        result = normalize(text)
        assert len(result.sections) == 1


class TestSemanticTypeMapping:
    def test_problems_maps_to_risks(self):
        text = "Problems:\n- x\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "risks"

    def test_risks_maps_to_risks(self):
        text = "Risks:\n- x\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "risks"

    def test_concerns_maps_to_risks(self):
        text = "Concerns:\n- x\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "risks"

    def test_next_step_maps_to_recommendation(self):
        text = "Next Step:\n- do it\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "recommendation"

    def test_next_steps_maps_to_recommendation(self):
        text = "Next Steps:\n- a\n- b\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "recommendation"

    def test_recommendation_maps_to_recommendation(self):
        text = "Recommendation:\n- adopt X\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "recommendation"

    def test_recommendations_maps_to_recommendation(self):
        text = "Recommendations:\n- a\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "recommendation"

    def test_focus_areas_maps_to_focus_areas(self):
        text = "Focus Areas:\n- telemetry\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "focus_areas"

    def test_focus_area_maps_to_focus_areas(self):
        text = "Focus Area:\n- telemetry\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "focus_areas"

    def test_metrics_maps_to_metrics(self):
        text = "Metrics:\n- deploy freq: 3/day\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "metrics"

    def test_results_maps_to_metrics(self):
        text = "Results:\n- 42 units shipped\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "metrics"

    def test_decisions_maps_to_decision(self):
        text = "Decisions:\n- use SQLite\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "decision"

    def test_open_questions_maps_to_open_questions(self):
        text = "Open Questions:\n- what is the SLA?\n"
        result = normalize(text)
        assert result.sections[0].semantic_type == "open_questions"


class TestUnknownLabels:
    def test_unknown_label_produces_general_type(self):
        # "Blockers:" is not in the known label list
        text = "Blockers:\n- pipeline delayed\n"
        result = normalize(text)
        # Should not produce any sections since "blockers" is not recognized
        assert all(s.semantic_type != "risks" or s.label.lower() != "blockers"
                   for s in result.sections)
        # And more specifically, has_labeled_sections returns False
        assert not has_labeled_sections(text)


class TestHasLabeledSections:
    def test_returns_true_for_labeled_text(self):
        assert has_labeled_sections(_LABELED_TEXT) is True

    def test_returns_false_for_plain_text(self):
        assert has_labeled_sections("Sprint 12 Summary\nVelocity: 38 story points") is False

    def test_returns_false_for_empty_string(self):
        assert has_labeled_sections("") is False

    def test_returns_true_when_label_has_leading_whitespace(self):
        # Labels with leading spaces should still be recognized after strip
        text = "  Problems:\n- x\n"
        assert has_labeled_sections(text) is True

    def test_returns_false_for_ado_connector_output(self):
        # Typical ADO connector output uses keyword-rich prose, not labels
        ado_text = (
            "Sprint 12 Summary\n"
            "Sprint velocity: 38 story points completed.\n"
            "Backlog: 14 items, 3 blocked by dependency.\n"
        )
        assert has_labeled_sections(ado_text) is False


class TestMultipleSectionsWithSameSemanticType:
    def test_two_risk_sections_both_present(self):
        text = "Problems:\n- x\nRisks:\n- y\n"
        result = normalize(text)
        assert len(result.sections) == 2
        assert all(s.semantic_type == "risks" for s in result.sections)
