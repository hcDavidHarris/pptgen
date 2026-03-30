"""Tests for the prompt registry — Phase 11B."""
from __future__ import annotations

import pytest

from pptgen.content_intelligence.prompts.prompt_registry import (
    EXPANSION,
    INSIGHT,
    NARRATIVE,
    get_expansion_prompt,
    get_insight_prompt,
    get_narrative_prompt,
    get_prompt,
)

_CTX_NARRATIVE = {"topic": "Cloud Migration", "goal": "Reduce costs", "audience": "CTO"}
_CTX_EXPANSION = {
    "title": "Cloud Migration: Problem",
    "intent_type": "problem",
    "key_points": ["Legacy costs are rising.", "Scalability is limited."],
    "topic": "Cloud Migration",
}
_CTX_INSIGHT = {
    "title": "Cloud Migration: Impact",
    "assertion": "Migration reduces opex by 40%.",
    "supporting_points": ["Lower hosting bills.", "Elastic scaling.", "Reduced headcount."],
}


class TestPromptConstants:
    def test_narrative_constant(self):
        assert NARRATIVE == "narrative"

    def test_expansion_constant(self):
        assert EXPANSION == "expansion"

    def test_insight_constant(self):
        assert INSIGHT == "insight"


class TestGetPromptDispatch:
    def test_narrative_via_get_prompt(self):
        prompt = get_prompt(NARRATIVE, _CTX_NARRATIVE)
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_expansion_via_get_prompt(self):
        prompt = get_prompt(EXPANSION, _CTX_EXPANSION)
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_insight_via_get_prompt(self):
        prompt = get_prompt(INSIGHT, _CTX_INSIGHT)
        assert isinstance(prompt, str) and len(prompt) > 0

    def test_unknown_name_raises_key_error(self):
        with pytest.raises(KeyError, match="nonexistent"):
            get_prompt("nonexistent", {})

    def test_get_prompt_matches_named_helper_narrative(self):
        assert get_prompt(NARRATIVE, _CTX_NARRATIVE) == get_narrative_prompt(_CTX_NARRATIVE)

    def test_get_prompt_matches_named_helper_expansion(self):
        assert get_prompt(EXPANSION, _CTX_EXPANSION) == get_expansion_prompt(_CTX_EXPANSION)

    def test_get_prompt_matches_named_helper_insight(self):
        assert get_prompt(INSIGHT, _CTX_INSIGHT) == get_insight_prompt(_CTX_INSIGHT)


class TestPromptContent:
    def test_narrative_prompt_embeds_topic(self):
        ctx = {"topic": "UNIQUE_TOPIC_XYZ", "goal": "", "audience": ""}
        assert "UNIQUE_TOPIC_XYZ" in get_narrative_prompt(ctx)

    def test_narrative_prompt_embeds_goal(self):
        ctx = {"topic": "T", "goal": "UNIQUE_GOAL_123", "audience": ""}
        assert "UNIQUE_GOAL_123" in get_narrative_prompt(ctx)

    def test_narrative_prompt_embeds_audience(self):
        ctx = {"topic": "T", "goal": "", "audience": "UNIQUE_AUDIENCE_456"}
        assert "UNIQUE_AUDIENCE_456" in get_narrative_prompt(ctx)

    def test_expansion_prompt_embeds_title(self):
        ctx = {**_CTX_EXPANSION, "title": "UNIQUE_TITLE_789"}
        assert "UNIQUE_TITLE_789" in get_expansion_prompt(ctx)

    def test_expansion_prompt_embeds_key_points(self):
        ctx = {**_CTX_EXPANSION, "key_points": ["UNIQUE_POINT_AAA"]}
        assert "UNIQUE_POINT_AAA" in get_expansion_prompt(ctx)

    def test_insight_prompt_embeds_assertion(self):
        ctx = {**_CTX_INSIGHT, "assertion": "UNIQUE_ASSERTION_BBB"}
        assert "UNIQUE_ASSERTION_BBB" in get_insight_prompt(ctx)

    def test_insight_prompt_embeds_supporting_points(self):
        ctx = {**_CTX_INSIGHT, "supporting_points": ["UNIQUE_PT_CCC"]}
        assert "UNIQUE_PT_CCC" in get_insight_prompt(ctx)


class TestPromptUniqueness:
    def test_all_three_prompts_are_distinct(self):
        prompts = [
            get_narrative_prompt(_CTX_NARRATIVE),
            get_expansion_prompt(_CTX_EXPANSION),
            get_insight_prompt(_CTX_INSIGHT),
        ]
        assert len(set(prompts)) == 3, "All prompt types must produce distinct strings"

    def test_different_topics_produce_different_narrative_prompts(self):
        p1 = get_narrative_prompt({"topic": "Topic A", "goal": "", "audience": ""})
        p2 = get_narrative_prompt({"topic": "Topic B", "goal": "", "audience": ""})
        assert p1 != p2


class TestPromptRobustness:
    def test_narrative_empty_optional_fields(self):
        prompt = get_narrative_prompt({"topic": "T", "goal": "", "audience": ""})
        assert isinstance(prompt, str) and len(prompt) > 10

    def test_expansion_empty_key_points(self):
        ctx = {"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"}
        prompt = get_expansion_prompt(ctx)
        assert isinstance(prompt, str) and len(prompt) > 10

    def test_insight_empty_supporting_points(self):
        ctx = {"title": "T", "assertion": "A.", "supporting_points": []}
        prompt = get_insight_prompt(ctx)
        assert isinstance(prompt, str) and len(prompt) > 10
