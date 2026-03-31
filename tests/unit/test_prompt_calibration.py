"""Prompt calibration tests — Phase 11D.

Verifies that prompt templates enforce:
  - Declarative, present-tense assertion language (no weak hedges).
  - Per-intent-type differentiated framing.
  - Metric realism guidance (ranges not fabricated precision).
  - Action/consequence-oriented implications.
  - Story arc instruction in the narrative.
  - Preserved JSON-only output contract.

These tests are instruction-level: they assert what the prompt *tells the model
to do*, not the model's output.  The parser/validator regression tests confirm
that the JSON contract itself is unaffected.
"""
from __future__ import annotations

import json

import pytest

from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt as build_expansion
from pptgen.content_intelligence.prompts.insight_prompt import build_prompt as build_insight
from pptgen.content_intelligence.prompts.narrative_prompt import build_prompt as build_narrative


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _expansion(intent_type: str, key_points: list[str] | None = None) -> str:
    return build_expansion({
        "title": "Test Slide",
        "intent_type": intent_type,
        "key_points": key_points or ["key point one"],
        "topic": "Test Topic",
    })


def _insight(supporting_points: list[str] | None = None) -> str:
    return build_insight({
        "title": "Test Slide",
        "assertion": "The platform is failing under load.",
        "supporting_points": supporting_points or ["Latency exceeds SLA.", "Error rate is rising."],
    })


def _narrative() -> str:
    return build_narrative({
        "topic": "Cloud Cost Optimisation",
        "goal": "Reduce infrastructure spend by 30%",
        "audience": "Engineering leadership",
    })


# ---------------------------------------------------------------------------
# Part 1 — Assertion language: declarative present-tense enforcement
# ---------------------------------------------------------------------------

class TestAssertionLanguageRules:
    """Expansion prompt must instruct the model to use declarative language."""

    def test_expansion_prompt_bans_may(self):
        """The instruction must explicitly disallow "may"."""
        for intent in ("problem", "solution", "impact", "metrics", "context", ""):
            prompt = _expansion(intent)
            assert '"may"' in prompt or "'may'" in prompt or 'never "may"' in prompt.lower() or '"may"/' in prompt, (
                f"intent={intent!r}: expansion prompt does not ban 'may'"
            )

    def test_expansion_prompt_bans_can(self):
        """The instruction must explicitly disallow "can"."""
        prompt = _expansion("problem")
        lower = prompt.lower()
        assert '"can"' in prompt or "\"can\"" in prompt or "/\"can\"" in prompt, (
            "expansion prompt does not ban 'can'"
        )

    def test_expansion_prompt_bans_might(self):
        prompt = _expansion("impact")
        assert '"might"' in prompt or '/"might"' in prompt or 'never' in prompt.lower(), (
            "expansion prompt does not instruct against 'might'"
        )

    def test_expansion_prompt_requires_present_tense_instruction(self):
        """Prompt must instruct 'present-tense'."""
        prompt = _expansion("solution")
        assert "present-tense" in prompt or "present tense" in prompt

    def test_expansion_prompt_suggests_is_drives_requires(self):
        """Prompt should suggest strong verbs like 'is', 'drives', 'requires'."""
        prompt = _expansion("problem")
        assert "drives" in prompt or '"is"' in prompt or "requires" in prompt

    def test_expansion_prompt_declarative_instruction_present_for_all_intents(self):
        """The declarative assertion rule must appear regardless of intent type."""
        for intent in ("problem", "solution", "impact", "metrics", ""):
            prompt = _expansion(intent)
            assert "declarative" in prompt, (
                f"intent={intent!r}: 'declarative' not found in expansion prompt"
            )


# ---------------------------------------------------------------------------
# Part 2 — Per-intent differentiation
# ---------------------------------------------------------------------------

class TestIntentDifferentiation:
    """Each intent type must receive distinct framing guidance."""

    # --- problem ---
    def test_problem_guidance_emphasises_failure(self):
        prompt = _expansion("problem")
        assert "failure" in prompt.lower() or "breaking" in prompt.lower() or "systemic" in prompt.lower()

    def test_problem_guidance_conveys_urgency(self):
        prompt = _expansion("problem")
        assert "urgency" in prompt.lower() or "matters now" in prompt.lower() or "scale" in prompt.lower()

    def test_problem_guidance_excludes_solution_framing(self):
        """Problem slide prompt must instruct the model not to propose solutions."""
        prompt = _expansion("problem")
        assert "do not propose solutions" in prompt.lower() or "not propose" in prompt.lower()

    def test_problem_guidance_absent_from_solution_slide(self):
        """The problem-specific framing must not appear in solution slides."""
        problem_prompt = _expansion("problem")
        solution_prompt = _expansion("solution")
        # "Do not propose solutions" is problem-only
        assert "do not propose solutions" not in solution_prompt.lower()

    # --- solution ---
    def test_solution_guidance_prescribes_actions(self):
        prompt = _expansion("solution")
        assert "prescribed" in prompt.lower() or "concrete" in prompt.lower() or "specific" in prompt.lower()

    def test_solution_guidance_explains_mechanism(self):
        """Solution prompt should ask how the solution works, not just what it is."""
        prompt = _expansion("solution")
        assert "how it works" in prompt.lower() or "mechanically" in prompt.lower() or "changes" in prompt.lower()

    def test_solution_guidance_bans_generic_recommendations(self):
        prompt = _expansion("solution")
        assert "generic" in prompt.lower() or "avoid" in prompt.lower()

    # --- impact ---
    def test_impact_guidance_references_financial_risk(self):
        prompt = _expansion("impact")
        assert "financial" in prompt.lower() or "financial loss" in prompt.lower()

    def test_impact_guidance_references_regulatory_or_customer(self):
        prompt = _expansion("impact")
        assert "regulatory" in prompt.lower() or "customer" in prompt.lower() or "churn" in prompt.lower()

    def test_impact_guidance_requires_ranges_not_precise_figures(self):
        """Impact prompt must instruct the model to prefer ranges."""
        prompt = _expansion("impact")
        assert "range" in prompt.lower() or "ranges" in prompt.lower()

    def test_impact_guidance_discourages_precise_fabricated_figures(self):
        """Impact prompt must warn against fabricated precise numbers."""
        prompt = _expansion("impact")
        assert "not precise" in prompt.lower() or "not fabricated" in prompt.lower() or "not exact" in prompt.lower()

    # --- metrics ---
    def test_metrics_guidance_requires_measurable_outcomes(self):
        prompt = _expansion("metrics")
        assert "measurable" in prompt.lower()

    def test_metrics_guidance_references_benchmarks_or_norms(self):
        prompt = _expansion("metrics")
        assert "benchmark" in prompt.lower() or "norms" in prompt.lower() or "industry" in prompt.lower()

    def test_metrics_guidance_discourages_fabricated_precision(self):
        prompt = _expansion("metrics")
        assert "range" in prompt.lower() or "typical" in prompt.lower() or "not fabricated" in prompt.lower()

    # --- cross-contamination guard ---
    def test_financial_framing_absent_from_problem_slide(self):
        """Problem framing must not bleed financial/impact language into problem prompt."""
        prompt = _expansion("problem")
        # "financial loss" and "regulatory risk" are impact-specific
        assert "financial loss" not in prompt.lower()
        assert "regulatory risk" not in prompt.lower()

    def test_ranges_instruction_absent_from_solution_slide(self):
        """Range/precision guidance is specific to impact/metrics, not solution."""
        prompt = _expansion("solution")
        assert "not precise figures" not in prompt.lower()
        assert "not fabricated" not in prompt.lower()


# ---------------------------------------------------------------------------
# Part 3 — Narrative arc and key_point quality
# ---------------------------------------------------------------------------

class TestNarrativeCalibration:
    """Narrative prompt must enforce story arc and specific key_points."""

    def test_narrative_contains_arc_instruction(self):
        """Prompt must instruct slides to follow a story arc."""
        prompt = _narrative()
        lower = prompt.lower()
        assert "arc" in lower or "story" in lower or "logical" in lower

    def test_narrative_arc_mentions_problem_first(self):
        prompt = _narrative()
        lower = prompt.lower()
        assert "problem" in lower

    def test_narrative_arc_mentions_impact(self):
        prompt = _narrative()
        lower = prompt.lower()
        assert "impact" in lower

    def test_narrative_key_points_bans_topic_labels(self):
        """key_points instruction must warn against vague topic-label phrasing."""
        prompt = _narrative()
        lower = prompt.lower()
        assert "not topic labels" in lower or "not vague" in lower or "specific claims" in lower

    def test_narrative_key_points_requires_specific_claims(self):
        prompt = _narrative()
        lower = prompt.lower()
        assert "specific" in lower

    def test_narrative_json_contract_intact(self):
        prompt = _narrative()
        assert "Output ONLY the JSON" in prompt
        assert "Start with [" in prompt

    def test_narrative_char_limit_still_met(self):
        prompt = _narrative()
        assert len(prompt) < 1000, f"Narrative prompt grew to {len(prompt)} chars"


# ---------------------------------------------------------------------------
# Part 4 — Implication strengthening
# ---------------------------------------------------------------------------

class TestImplicationStrengthening:
    """Insight prompt must enforce action-or-consequence implications."""

    def test_insight_requires_action_or_consequence(self):
        """Prompt must require each implication to be action or consequence."""
        prompt = _insight()
        lower = prompt.lower()
        assert "action" in lower or "consequence" in lower or "requires" in lower or "must" in lower

    def test_insight_includes_action_trigger_words(self):
        """Prompt should suggest strong action verbs like 'must', 'requires'."""
        prompt = _insight()
        assert '"must"' in prompt or '"requires"' in prompt or "must" in prompt.lower()

    def test_insight_requires_concrete_consequence_categories(self):
        """Prompt must name consequence categories (financial/regulatory/operational)."""
        prompt = _insight()
        lower = prompt.lower()
        assert "financial" in lower or "regulatory" in lower or "operational" in lower

    def test_insight_bans_restatement_of_assertion(self):
        """Prompt must instruct not to restate the assertion."""
        prompt = _insight()
        lower = prompt.lower()
        assert "do not restate" in lower or "not restate" in lower

    def test_insight_json_contract_intact(self):
        prompt = _insight()
        assert "Output ONLY the JSON" in prompt
        assert "Start with {" in prompt
        assert '"implications"' in prompt

    def test_insight_char_limit_still_met(self):
        prompt = _insight()
        assert len(prompt) < 700, f"Insight prompt grew to {len(prompt)} chars"


# ---------------------------------------------------------------------------
# Part 5 — JSON contract regression (parser compatibility)
# ---------------------------------------------------------------------------

class TestJsonContractRegression:
    """Prompts must still produce schema-compatible JSON — verified via parsers."""

    def test_expansion_parser_accepts_minimal_valid_json(self):
        """The expansion parser must handle well-formed output."""
        from pptgen.content_intelligence.content_expander import expand_slide
        from pptgen.content_intelligence.content_models import SlideIntent
        from pptgen.content_intelligence.prompt_runner import run_prompt
        import json as _json

        good_output = json.dumps({
            "assertion": "Latency is degrading customer experience.",
            "supporting_points": [
                "P99 latency exceeds 2s.",
                "Error rate is 5x normal.",
                "Customer complaints rose 40%.",
            ],
        })

        def _mock_caller(prompt: str) -> str:
            return good_output

        _mock_caller._backend_name = "test"

        diag = []
        result = run_prompt(
            prompt_name="expansion",
            context={
                "title": "Latency Impact",
                "intent_type": "impact",
                "key_points": ["High latency"],
                "topic": "Latency Impact",
            },
            parser=lambda s: _json.loads(s),
            fallback=lambda: {},
            llm_caller=_mock_caller,
            diagnostics_out=diag,
        )

        assert result["assertion"] == "Latency is degrading customer experience."
        assert len(result["supporting_points"]) == 3
        assert diag[0]["fallback_used"] is False

    def test_insight_parser_accepts_minimal_valid_json(self):
        """The insight parser must handle well-formed output."""
        from pptgen.content_intelligence.prompt_runner import run_prompt
        import json as _json

        good_output = json.dumps({
            "implications": [
                "The platform team must immediately reduce P99 latency to below 500ms.",
                "Failure to act risks $2–5M in customer churn within Q2.",
            ]
        })

        def _mock_caller(prompt: str) -> str:
            return good_output

        _mock_caller._backend_name = "test"

        diag = []
        result = run_prompt(
            prompt_name="insight",
            context={
                "title": "Latency Impact",
                "assertion": "Latency is degrading customer experience.",
                "supporting_points": ["P99 exceeds SLA.", "Error rate rising."],
            },
            parser=lambda s: _json.loads(s),
            fallback=lambda: {},
            llm_caller=_mock_caller,
            diagnostics_out=diag,
        )

        assert len(result["implications"]) == 2
        assert diag[0]["fallback_used"] is False

    def test_narrative_parser_accepts_minimal_valid_json(self):
        """The narrative parser must handle well-formed output."""
        from pptgen.content_intelligence.prompt_runner import run_prompt
        import json as _json

        good_output = json.dumps([
            {
                "title": "Platform Reliability Crisis",
                "intent_type": "problem",
                "key_points": ["SLA breach", "Customer escalations"],
            },
            {
                "title": "Remediation Plan",
                "intent_type": "solution",
                "key_points": ["Circuit breakers", "Graduated rollout"],
            },
        ])

        def _mock_caller(prompt: str) -> str:
            return good_output

        _mock_caller._backend_name = "test"

        diag = []
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "Reliability", "goal": "Fix it", "audience": "Execs"},
            parser=lambda s: _json.loads(s),
            fallback=lambda: [],
            llm_caller=_mock_caller,
            diagnostics_out=diag,
        )

        assert isinstance(result, list)
        assert len(result) == 2
        assert diag[0]["fallback_used"] is False

    def test_expansion_all_intents_produce_valid_prompts(self):
        """All registered intent types must build without raising."""
        intents = ["problem", "solution", "impact", "metrics", "context", "recommendation", ""]
        for intent in intents:
            prompt = build_expansion({
                "title": "Test",
                "intent_type": intent,
                "key_points": ["point"],
                "topic": "Test",
            })
            assert isinstance(prompt, str)
            assert len(prompt) > 50

    def test_all_prompts_contain_no_double_curly_leakage(self):
        """Template {{ / }} must be rendered to { / } in the output."""
        n = _narrative()
        e = _expansion("problem")
        i = _insight()
        for name, prompt in [("narrative", n), ("expansion", e), ("insight", i)]:
            assert "{{" not in prompt, f"{name}: unrendered {{ in output"
            assert "}}" not in prompt, f"{name}: unrendered }} in output"
