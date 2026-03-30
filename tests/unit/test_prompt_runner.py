"""Tests for the prompt runner — Phase 11B."""
from __future__ import annotations

import json

import pytest

from pptgen.content_intelligence.prompt_runner import extract_json, run_prompt


# ---------------------------------------------------------------------------
# extract_json
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_plain_json_returned_unchanged(self):
        raw = '{"key": "value"}'
        assert extract_json(raw) == '{"key": "value"}'

    def test_strips_json_fence(self):
        raw = "```json\n{\"key\": \"value\"}\n```"
        assert extract_json(raw) == '{"key": "value"}'

    def test_strips_plain_fence(self):
        raw = "```\n{\"key\": \"value\"}\n```"
        assert extract_json(raw) == '{"key": "value"}'

    def test_strips_whitespace_only(self):
        raw = "  \n  [1, 2, 3]  \n  "
        assert extract_json(raw) == "[1, 2, 3]"

    def test_array_json_unchanged(self):
        raw = '[{"a": 1}]'
        assert extract_json(raw) == '[{"a": 1}]'

    # --- <think> block stripping (qwen3 / reasoning models) ---

    def test_strips_think_block_before_json_object(self):
        raw = "<think>\nsome reasoning here\n</think>\n{\"key\": \"value\"}"
        assert extract_json(raw) == '{"key": "value"}'

    def test_strips_think_block_before_json_array(self):
        raw = "<think>reasoning</think>[1, 2, 3]"
        assert extract_json(raw) == "[1, 2, 3]"

    def test_strips_think_block_case_insensitive(self):
        raw = "<THINK>reasoning</THINK>{\"x\": 1}"
        assert extract_json(raw) == '{"x": 1}'

    def test_strips_think_block_before_code_fence(self):
        raw = "<think>reasoning</think>\n```json\n{\"k\": 1}\n```"
        assert extract_json(raw) == '{"k": 1}'

    def test_strips_multiline_think_block(self):
        raw = "<think>\nLine 1\nLine 2\nLine 3\n</think>\n{\"result\": true}"
        assert extract_json(raw) == '{"result": true}'

    # --- prose-prefixed responses ---

    def test_scans_past_prose_to_json_object(self):
        raw = "Here is the JSON:\n{\"key\": \"value\"}"
        result = extract_json(raw)
        assert result.startswith("{")
        import json
        assert json.loads(result) == {"key": "value"}

    def test_scans_past_prose_to_json_array(self):
        raw = "Sure! [1, 2, 3]"
        result = extract_json(raw)
        assert result.startswith("[")
        import json
        assert json.loads(result) == [1, 2, 3]

    def test_think_then_prose_then_json(self):
        raw = "<think>reasoning</think>\nHere you go:\n{\"a\": 1}"
        result = extract_json(raw)
        import json
        assert json.loads(result) == {"a": 1}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_llm(response: str):
    """Return a callable that always returns *response*."""
    return lambda prompt: response  # noqa: ARG005


def _raising_parser(raw: str):
    raise ValueError("intentional parse failure")


def _raising_llm(prompt: str) -> str:
    raise RuntimeError("network error")


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


class TestRunPromptSuccess:
    def test_returns_parsed_value(self):
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "Cloud", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm('[{"title":"T","intent_type":"p","key_points":["x"]}]'),
        )
        assert isinstance(result, list)
        assert result[0]["title"] == "T"

    def test_strips_code_fence_before_parsing(self):
        fenced = "```json\n{\"x\": 42}\n```"
        result = run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: {},
            llm_caller=_mock_llm(fenced),
        )
        assert result == {"x": 42}

    def test_validator_accepts_valid_result(self):
        result = run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=lambda x: isinstance(x, dict) and "ok" in x,
            llm_caller=_mock_llm('{"ok": true}'),
        )
        assert result == {"ok": True}

    def test_no_validator_skips_validation(self):
        result = run_prompt(
            prompt_name="insight",
            context={"title": "T", "assertion": "A", "supporting_points": []},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=None,
            llm_caller=_mock_llm('{"anything": "goes"}'),
        )
        assert result == {"anything": "goes"}

    def test_metadata_preserved_through_runner(self):
        from pptgen.content_intelligence.content_models import EnrichedSlideContent

        response = '{"assertion": "Big claim.", "supporting_points": ["a", "b", "c"]}'

        def _parse(raw: str) -> EnrichedSlideContent:
            d = json.loads(raw)
            return EnrichedSlideContent(
                title="T",
                assertion=d["assertion"],
                supporting_points=d["supporting_points"],
                metadata={"source": "prompt"},
            )

        result = run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "solution", "key_points": [], "topic": "T"},
            parser=_parse,
            fallback=lambda: EnrichedSlideContent(title="T"),
            llm_caller=_mock_llm(response),
        )
        assert result.metadata.get("source") == "prompt"


# ---------------------------------------------------------------------------
# Fallback paths
# ---------------------------------------------------------------------------


class TestRunPromptFallback:
    def test_llm_exception_triggers_fallback(self):
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_raising_llm,
        )
        assert result == "FALLBACK"

    def test_parse_exception_triggers_fallback(self):
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=_raising_parser,
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("valid but parser rejects it"),
        )
        assert result == "FALLBACK"

    def test_invalid_json_triggers_fallback(self):
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("this is {{ not json"),
        )
        assert result == "FALLBACK"

    def test_validator_false_triggers_fallback(self):
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=lambda x: False,
            llm_caller=_mock_llm('{"valid": "json"}'),
        )
        assert result == "FALLBACK"

    def test_validator_exception_triggers_fallback(self):
        def _bad_validator(x):
            raise RuntimeError("validator blew up")

        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=_bad_validator,
            llm_caller=_mock_llm('{"valid": "json"}'),
        )
        assert result == "FALLBACK"

    def test_no_llm_configured_triggers_fallback(self):
        """Default caller with mock provider must fall through to fallback."""
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            result = run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                # llm_caller intentionally omitted — uses default
            )
            assert result == "FALLBACK"
        finally:
            override_settings(None)

    def test_fallback_called_exactly_once_on_llm_error(self):
        call_count = {"n": 0}

        def _fallback():
            call_count["n"] += 1
            return "FALLBACK"

        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=_fallback,
            llm_caller=_raising_llm,
        )
        assert call_count["n"] == 1

    def test_fallback_value_passes_through_unchanged(self):
        sentinel = object()
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=_raising_parser,
            fallback=lambda: sentinel,
            llm_caller=_mock_llm("bad"),
        )
        assert result is sentinel
