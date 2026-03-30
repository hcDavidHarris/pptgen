"""Diagnostic observability tests for the prompt runner — Phase 11 diagnosis.

These tests make the fallback execution path explicit and machine-verifiable.
They directly answer the question: "Is the LLM path running, or is the system
always falling back?" and prevent silent fallback from being ambiguous again.

Root cause confirmed: with the default model_provider="mock" (no API key),
run_prompt() ALWAYS falls back with reason="no_llm".  The LLM is never called.
"""
from __future__ import annotations

import json
import logging

import pytest

from pptgen.content_intelligence.prompt_runner import (
    FALLBACK_REASON_BUILD_ERROR,
    FALLBACK_REASON_EXECUTION_ERROR,
    FALLBACK_REASON_NO_LLM,
    FALLBACK_REASON_NONE,
    FALLBACK_REASON_PARSE_ERROR,
    FALLBACK_REASON_VALIDATION_FAILURE,
    _no_llm_configured,
    run_prompt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_llm(response: str):
    return lambda prompt: response  # noqa: ARG005


def _raising_llm(prompt: str) -> str:
    raise RuntimeError("network error")


# ---------------------------------------------------------------------------
# diagnostics_out — success path
# ---------------------------------------------------------------------------

class TestDiagnosticsSuccess:
    def test_success_records_fallback_used_false(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm('[{"title":"T","intent_type":"p","key_points":[]}]'),
            diagnostics_out=diag,
        )
        assert len(diag) == 1
        assert diag[0]["fallback_used"] is False

    def test_success_records_reason_none(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm('{"ok": true}'),
            diagnostics_out=diag,
        )
        assert diag[0]["fallback_reason"] == FALLBACK_REASON_NONE

    def test_success_records_backend_called_true(self):
        diag = []
        run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: {},
            llm_caller=_mock_llm('{"ok": 1}'),
            diagnostics_out=diag,
        )
        assert diag[0]["backend_called"] is True

    def test_success_records_raw_output_length(self):
        response = '{"ok": true}'
        diag = []
        run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: {},
            llm_caller=_mock_llm(response),
            diagnostics_out=diag,
        )
        assert diag[0]["raw_output_length"] == len(response)

    def test_success_records_parse_succeeded_true(self):
        diag = []
        run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: {},
            llm_caller=_mock_llm('{"ok": 1}'),
            diagnostics_out=diag,
        )
        assert diag[0]["parse_succeeded"] is True

    def test_success_records_prompt_name(self):
        diag = []
        run_prompt(
            prompt_name="insight",
            context={"title": "T", "assertion": "A", "supporting_points": []},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: {},
            llm_caller=_mock_llm('{"ok": 1}'),
            diagnostics_out=diag,
        )
        assert diag[0]["prompt_name"] == "insight"

    def test_success_records_backend_configured(self):
        diag = []
        run_prompt(
            prompt_name="insight",
            context={"title": "T", "assertion": "A", "supporting_points": []},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: {},
            llm_caller=_mock_llm('{"ok": 1}'),
            diagnostics_out=diag,
        )
        assert diag[0]["backend"] == "configured"

    def test_no_diagnostics_out_still_works(self):
        """Omitting diagnostics_out must not break run_prompt."""
        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm('{"ok": 1}'),
        )
        assert result == {"ok": 1}

    def test_exactly_one_diag_appended_on_success(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm('{"ok": 1}'),
            diagnostics_out=diag,
        )
        assert len(diag) == 1


# ---------------------------------------------------------------------------
# diagnostics_out — no_llm fallback (the real-world default case)
# ---------------------------------------------------------------------------

class TestDiagnosticsNoLLM:
    """These tests document the CURRENT behaviour when model_provider='mock'."""

    def test_no_llm_configured_reason(self):
        """When the default unconfigured caller is used, fallback_reason=no_llm."""
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            diag = []
            run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                diagnostics_out=diag,
            )
            assert len(diag) == 1
            assert diag[0]["fallback_reason"] == FALLBACK_REASON_NO_LLM
        finally:
            override_settings(None)

    def test_no_llm_backend_name(self):
        """The diagnostic backend field must explicitly identify the stub."""
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            diag = []
            run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                diagnostics_out=diag,
            )
            assert diag[0]["backend"] == "no_llm_configured"
        finally:
            override_settings(None)

    def test_no_llm_backend_not_called(self):
        """With no LLM, backend_called must be False — the stub is detected upfront."""
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            diag = []
            run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                diagnostics_out=diag,
            )
            assert diag[0]["backend_called"] is False
        finally:
            override_settings(None)

    def test_no_llm_fallback_used(self):
        from pptgen.config import RuntimeSettings, override_settings

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            diag = []
            result = run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                diagnostics_out=diag,
            )
            assert result == "FALLBACK"
            assert diag[0]["fallback_used"] is True
        finally:
            override_settings(None)

    def test_no_llm_stub_is_identifiable_from_caller(self):
        """The _no_llm_configured function must be the exact object returned by
        the default caller when no API key is set — callers can check identity."""
        from pptgen.config import RuntimeSettings, override_settings
        from pptgen.content_intelligence.prompt_runner import _make_default_caller

        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            caller = _make_default_caller()
            assert caller is _no_llm_configured, (
                "Default caller with model_provider='mock' must be _no_llm_configured. "
                "If this fails, an unintended LLM backend has been wired in."
            )
        finally:
            override_settings(None)


# ---------------------------------------------------------------------------
# diagnostics_out — execution_error fallback
# ---------------------------------------------------------------------------

class TestDiagnosticsExecutionError:
    def test_execution_error_reason(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_raising_llm,
            diagnostics_out=diag,
        )
        assert diag[0]["fallback_reason"] == FALLBACK_REASON_EXECUTION_ERROR

    def test_execution_error_backend_called_true(self):
        """A configured-but-failing backend marks backend_called=True."""
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_raising_llm,
            diagnostics_out=diag,
        )
        assert diag[0]["backend_called"] is True

    def test_execution_error_backend_name_is_configured(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_raising_llm,
            diagnostics_out=diag,
        )
        assert diag[0]["backend"] == "configured"


# ---------------------------------------------------------------------------
# diagnostics_out — parse_error fallback
# ---------------------------------------------------------------------------

class TestDiagnosticsParseError:
    def test_parse_error_reason(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("this is not json {{"),
            diagnostics_out=diag,
        )
        assert diag[0]["fallback_reason"] == FALLBACK_REASON_PARSE_ERROR

    def test_parse_error_parse_succeeded_false(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("this is not json"),
            diagnostics_out=diag,
        )
        assert diag[0]["parse_succeeded"] is False

    def test_parse_error_backend_called_true(self):
        """Backend was called — we got output, it just wasn't parseable."""
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("not json"),
            diagnostics_out=diag,
        )
        assert diag[0]["backend_called"] is True

    def test_parse_error_records_raw_output_length(self):
        response = "not valid json at all"
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm(response),
            diagnostics_out=diag,
        )
        # raw_output_length is set before parse attempt
        assert diag[0]["raw_output_length"] == len(response)


# ---------------------------------------------------------------------------
# diagnostics_out — validation_failure fallback
# ---------------------------------------------------------------------------

class TestDiagnosticsValidationFailure:
    def test_validation_failure_reason(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=lambda x: False,
            llm_caller=_mock_llm('{"valid": "json"}'),
            diagnostics_out=diag,
        )
        assert diag[0]["fallback_reason"] == FALLBACK_REASON_VALIDATION_FAILURE

    def test_validation_failure_validation_succeeded_false(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=lambda x: False,
            llm_caller=_mock_llm('{"valid": "json"}'),
            diagnostics_out=diag,
        )
        assert diag[0]["validation_succeeded"] is False

    def test_validation_succeeded_true_on_success(self):
        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=lambda x: True,
            llm_caller=_mock_llm('{"valid": "json"}'),
            diagnostics_out=diag,
        )
        assert diag[0]["validation_succeeded"] is True

    def test_validator_exception_records_failure(self):
        def _bad_validator(x):
            raise RuntimeError("validator blew up")

        diag = []
        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            validator=_bad_validator,
            llm_caller=_mock_llm('{"valid": "json"}'),
            diagnostics_out=diag,
        )
        assert diag[0]["fallback_reason"] == FALLBACK_REASON_VALIDATION_FAILURE
        assert diag[0]["validation_succeeded"] is False


# ---------------------------------------------------------------------------
# diagnostics_out — build_error fallback
# ---------------------------------------------------------------------------

class TestDiagnosticsBuildError:
    def test_build_error_reason(self):
        diag = []
        run_prompt(
            prompt_name="__nonexistent_prompt__",
            context={},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("irrelevant"),
            diagnostics_out=diag,
        )
        assert diag[0]["fallback_reason"] == FALLBACK_REASON_BUILD_ERROR

    def test_build_error_backend_not_called(self):
        """When prompt build fails, the backend must not be called."""
        diag = []
        run_prompt(
            prompt_name="__nonexistent_prompt__",
            context={},
            parser=lambda raw: json.loads(raw),
            fallback=lambda: "FALLBACK",
            llm_caller=_mock_llm("irrelevant"),
            diagnostics_out=diag,
        )
        assert diag[0]["backend_called"] is False


# ---------------------------------------------------------------------------
# Fallback WARNING logging
# ---------------------------------------------------------------------------

class TestFallbackLogging:
    def test_fallback_emits_warning_log(self, caplog):
        """Any fallback must emit at least one WARNING-level log."""
        with caplog.at_level(logging.WARNING, logger="pptgen.content_intelligence.prompt_runner"):
            run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                llm_caller=_raising_llm,
            )
        assert any("fallback" in r.message.lower() for r in caplog.records)

    def test_fallback_log_includes_prompt_name(self, caplog):
        with caplog.at_level(logging.WARNING, logger="pptgen.content_intelligence.prompt_runner"):
            run_prompt(
                prompt_name="expansion",
                context={"title": "T", "intent_type": "p", "key_points": [], "topic": "T"},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                llm_caller=_raising_llm,
            )
        assert any("expansion" in r.message for r in caplog.records)

    def test_success_does_not_emit_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="pptgen.content_intelligence.prompt_runner"):
            run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda raw: json.loads(raw),
                fallback=lambda: "FALLBACK",
                llm_caller=_mock_llm('{"ok": 1}'),
            )
        assert len(caplog.records) == 0


# ---------------------------------------------------------------------------
# Prompt metadata propagation — expander and insight carry _prompt_diag
# ---------------------------------------------------------------------------

class TestPromptDiagnosticsInMetadata:
    """Verify that EnrichedSlideContent.metadata carries _prompt_diag."""

    def test_expand_slide_metadata_has_prompt_diag(self):
        from pptgen.content_intelligence.content_expander import expand_slide
        from pptgen.content_intelligence.content_models import SlideIntent

        slide = SlideIntent(title="Cloud Cost", intent_type="problem", key_points=["Cost too high"])
        result = expand_slide(slide)
        assert "_prompt_diag" in result.metadata, (
            "expand_slide must embed _prompt_diag in metadata. "
            "This proves the prompt path was attempted and records why fallback fired."
        )

    def test_expand_slide_prompt_diag_has_fallback_reason(self):
        from pptgen.content_intelligence.content_expander import expand_slide
        from pptgen.content_intelligence.content_models import SlideIntent

        slide = SlideIntent(title="Cloud Cost", intent_type="problem", key_points=[])
        result = expand_slide(slide)
        diag = result.metadata["_prompt_diag"]
        assert "fallback_reason" in diag

    def test_expand_slide_no_llm_shows_in_diag(self):
        """With default settings (model_provider=mock), expansion always falls back."""
        from pptgen.content_intelligence.content_expander import expand_slide
        from pptgen.content_intelligence.content_models import SlideIntent

        slide = SlideIntent(title="Platform Strategy", intent_type="solution", key_points=[])
        result = expand_slide(slide)
        diag = result.metadata.get("_prompt_diag", {})
        # Confirms root cause: no_llm is always the fallback reason in default config
        assert diag.get("fallback_reason") in (FALLBACK_REASON_NO_LLM, FALLBACK_REASON_EXECUTION_ERROR), (
            f"Expected no_llm or execution_error fallback, got: {diag}. "
            "If this fails, an LLM IS configured and the prompt path may be running."
        )

    def test_generate_insights_metadata_has_prompt_diag(self):
        from pptgen.content_intelligence.content_models import EnrichedSlideContent
        from pptgen.content_intelligence.insight_generator import generate_insights

        content = EnrichedSlideContent(
            title="Cost Strategy",
            assertion="Costs must be reduced.",
            supporting_points=["Point A", "Point B", "Point C"],
        )
        result = generate_insights(content)
        assert "_prompt_diag" in result.metadata

    def test_generate_insights_no_llm_shows_in_diag(self):
        from pptgen.content_intelligence.content_models import EnrichedSlideContent
        from pptgen.content_intelligence.insight_generator import generate_insights

        content = EnrichedSlideContent(
            title="Risk",
            assertion="Risks are high.",
            supporting_points=["Risk A", "Risk B", "Risk C"],
        )
        result = generate_insights(content)
        diag = result.metadata.get("_prompt_diag", {})
        assert diag.get("fallback_reason") in (FALLBACK_REASON_NO_LLM, FALLBACK_REASON_EXECUTION_ERROR)

    def test_source_is_content_expander_when_falling_back(self):
        """When fallback fires in expand_slide, metadata source must be 'content_expander'."""
        from pptgen.content_intelligence.content_expander import expand_slide
        from pptgen.content_intelligence.content_models import SlideIntent

        slide = SlideIntent(title="T", intent_type="problem", key_points=[])
        result = expand_slide(slide)
        assert result.metadata.get("source") == "content_expander", (
            "Fallback path must mark source='content_expander', not 'prompt'. "
            "If 'prompt' is seen here, the LLM path ran successfully."
        )
