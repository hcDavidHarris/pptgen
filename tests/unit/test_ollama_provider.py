"""Tests for the Ollama provider integration — prompt_runner + settings.

Covers:
  - Provider selection (ollama / anthropic / unknown → _no_llm_configured)
  - Successful HTTP call (mocked requests.post)
  - Failure paths (HTTP error, empty response, connection error)
  - Diagnostics observability (backend="ollama", fallback reasons)
  - End-to-end through run_prompt() with a mocked Ollama response
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from pptgen.config import RuntimeSettings, override_settings
from pptgen.content_intelligence.prompt_runner import (
    FALLBACK_REASON_EXECUTION_ERROR,
    FALLBACK_REASON_NO_LLM,
    FALLBACK_REASON_NONE,
    _build_ollama_caller,
    _make_default_caller,
    _no_llm_configured,
    run_prompt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ollama_settings(**overrides) -> RuntimeSettings:
    """Return a RuntimeSettings with model_provider='ollama'."""
    defaults = dict(
        model_provider="ollama",
        ollama_model="qwen3:latest",
        ollama_base_url="http://localhost:11434",
    )
    defaults.update(overrides)
    return RuntimeSettings(**defaults)


def _mock_response(text: str, status_code: int = 200) -> MagicMock:
    """Return a mock requests.Response for a successful Ollama reply."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {"response": text, "done": True}
    resp.raise_for_status = MagicMock()  # no-op for 200
    return resp


def _mock_error_response(status_code: int = 500) -> MagicMock:
    """Return a mock that raises HTTPError when raise_for_status() is called."""
    import requests

    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status.side_effect = requests.HTTPError(
        f"{status_code} Server Error", response=resp
    )
    return resp


# ---------------------------------------------------------------------------
# Part 1 — Provider selection
# ---------------------------------------------------------------------------

class TestProviderSelection:
    def test_ollama_provider_returns_callable(self):
        override_settings(_ollama_settings())
        try:
            caller = _make_default_caller()
            assert callable(caller)
            assert caller is not _no_llm_configured
        finally:
            override_settings(None)

    def test_ollama_provider_backend_name_is_ollama(self):
        override_settings(_ollama_settings())
        try:
            caller = _make_default_caller()
            assert getattr(caller, "_backend_name", None) == "ollama"
        finally:
            override_settings(None)

    def test_unknown_provider_returns_no_llm_configured(self):
        override_settings(RuntimeSettings(model_provider="openai", model_api_key=""))
        try:
            caller = _make_default_caller()
            assert caller is _no_llm_configured
        finally:
            override_settings(None)

    def test_mock_provider_returns_no_llm_configured(self):
        override_settings(RuntimeSettings(model_provider="mock", model_api_key=""))
        try:
            caller = _make_default_caller()
            assert caller is _no_llm_configured
        finally:
            override_settings(None)

    def test_anthropic_without_key_returns_no_llm_configured(self):
        override_settings(RuntimeSettings(model_provider="anthropic", model_api_key=""))
        try:
            caller = _make_default_caller()
            assert caller is _no_llm_configured
        finally:
            override_settings(None)

    def test_anthropic_with_key_returns_callable(self):
        override_settings(RuntimeSettings(model_provider="anthropic", model_api_key="sk-test"))
        try:
            caller = _make_default_caller()
            assert callable(caller)
            assert caller is not _no_llm_configured
        finally:
            override_settings(None)

    def test_anthropic_backend_name(self):
        override_settings(RuntimeSettings(model_provider="anthropic", model_api_key="sk-test"))
        try:
            caller = _make_default_caller()
            assert getattr(caller, "_backend_name", None) == "anthropic"
        finally:
            override_settings(None)

    def test_ollama_uses_configured_model(self):
        """_build_ollama_caller uses the model from settings."""
        override_settings(_ollama_settings(ollama_model="llama3.2:latest"))
        try:
            with patch("requests.post", return_value=_mock_response("hello")) as mock_post:
                caller = _make_default_caller()
                caller("test prompt")
            call_kwargs = mock_post.call_args
            payload = call_kwargs[1]["json"] if call_kwargs[1] else call_kwargs[0][1]
            assert payload["model"] == "llama3.2:latest"
        finally:
            override_settings(None)

    def test_ollama_uses_configured_base_url(self):
        override_settings(_ollama_settings(ollama_base_url="http://192.168.1.10:11434"))
        try:
            with patch("requests.post", return_value=_mock_response("hello")) as mock_post:
                caller = _make_default_caller()
                caller("test")
            url = mock_post.call_args[0][0]
            assert url.startswith("http://192.168.1.10:11434")
        finally:
            override_settings(None)


# ---------------------------------------------------------------------------
# Part 2 — Successful Ollama call (mocked HTTP)
# ---------------------------------------------------------------------------

class TestOllamaSuccessPath:
    def test_returns_response_text(self):
        with patch("requests.post", return_value=_mock_response("Real generated content.")):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            result = caller("some prompt")
        assert result == "Real generated content."

    def test_strips_trailing_whitespace(self):
        with patch("requests.post", return_value=_mock_response("  content  \n")):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            result = caller("prompt")
        assert result == "content"

    def test_posts_to_correct_endpoint(self):
        with patch("requests.post", return_value=_mock_response("ok")) as mock_post:
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            caller("prompt")
        url = mock_post.call_args[0][0]
        assert url == "http://localhost:11434/api/generate"

    def test_sends_stream_false(self):
        with patch("requests.post", return_value=_mock_response("ok")) as mock_post:
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            caller("prompt")
        payload = mock_post.call_args[1]["json"]
        assert payload["stream"] is False

    def test_sends_correct_model(self):
        with patch("requests.post", return_value=_mock_response("ok")) as mock_post:
            caller = _build_ollama_caller("http://localhost:11434", "mistral:latest")
            caller("prompt")
        payload = mock_post.call_args[1]["json"]
        assert payload["model"] == "mistral:latest"

    def test_sends_prompt_in_payload(self):
        with patch("requests.post", return_value=_mock_response("ok")) as mock_post:
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            caller("my test prompt")
        payload = mock_post.call_args[1]["json"]
        assert payload["prompt"] == "my test prompt"

    def test_timeout_default_is_120(self):
        with patch("requests.post", return_value=_mock_response("ok")) as mock_post:
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            caller("prompt")
        assert mock_post.call_args[1]["timeout"] == 120


# ---------------------------------------------------------------------------
# Part 3 — Failure paths (all must propagate — NOT caught by caller)
# ---------------------------------------------------------------------------

class TestOllamaFailurePaths:
    def test_http_error_propagates(self):
        with patch("requests.post", return_value=_mock_error_response(500)):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            with pytest.raises(Exception):
                caller("prompt")

    def test_empty_response_raises_runtime_error(self):
        empty_resp = MagicMock()
        empty_resp.raise_for_status = MagicMock()
        empty_resp.json.return_value = {"response": "", "done": True}
        with patch("requests.post", return_value=empty_resp):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            with pytest.raises(RuntimeError, match="empty response"):
                caller("prompt")

    def test_missing_response_key_raises(self):
        no_key_resp = MagicMock()
        no_key_resp.raise_for_status = MagicMock()
        no_key_resp.json.return_value = {"done": True}  # no "response" key
        with patch("requests.post", return_value=no_key_resp):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            with pytest.raises(RuntimeError, match="empty response"):
                caller("prompt")

    def test_connection_error_propagates(self):
        import requests as _requests
        with patch("requests.post", side_effect=_requests.ConnectionError("refused")):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            with pytest.raises(_requests.ConnectionError):
                caller("prompt")

    def test_timeout_propagates(self):
        import requests as _requests
        with patch("requests.post", side_effect=_requests.Timeout("timed out")):
            caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
            with pytest.raises(_requests.Timeout):
                caller("prompt")


# ---------------------------------------------------------------------------
# Part 4 — Diagnostics observability
# ---------------------------------------------------------------------------

class TestOllamaDiagnostics:
    def test_backend_name_is_ollama_in_diag(self):
        """Diagnostics must show backend='ollama', not 'configured'."""
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch(
                "requests.post",
                return_value=_mock_response('{"response": "hi"}'),
            ):
                run_prompt(
                    prompt_name="narrative",
                    context={"topic": "T", "goal": "", "audience": ""},
                    parser=lambda raw: raw,
                    fallback=lambda: "FALLBACK",
                    diagnostics_out=diag,
                )
            assert diag[0]["backend"] == "ollama"
        finally:
            override_settings(None)

    def test_no_llm_reason_not_triggered_for_ollama(self):
        """FALLBACK_REASON_NO_LLM must NOT fire when model_provider='ollama'."""
        import requests as _requests
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch(
                "requests.post",
                side_effect=_requests.ConnectionError("refused"),
            ):
                run_prompt(
                    prompt_name="narrative",
                    context={"topic": "T", "goal": "", "audience": ""},
                    parser=lambda raw: raw,
                    fallback=lambda: "FALLBACK",
                    diagnostics_out=diag,
                )
            assert diag[0]["fallback_reason"] != FALLBACK_REASON_NO_LLM
        finally:
            override_settings(None)

    def test_execution_error_reason_on_connection_failure(self):
        import requests as _requests
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch(
                "requests.post",
                side_effect=_requests.ConnectionError("refused"),
            ):
                run_prompt(
                    prompt_name="narrative",
                    context={"topic": "T", "goal": "", "audience": ""},
                    parser=lambda raw: raw,
                    fallback=lambda: "FALLBACK",
                    diagnostics_out=diag,
                )
            assert diag[0]["fallback_reason"] == FALLBACK_REASON_EXECUTION_ERROR
        finally:
            override_settings(None)

    def test_execution_error_reason_on_http_error(self):
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch("requests.post", return_value=_mock_error_response(503)):
                run_prompt(
                    prompt_name="narrative",
                    context={"topic": "T", "goal": "", "audience": ""},
                    parser=lambda raw: raw,
                    fallback=lambda: "FALLBACK",
                    diagnostics_out=diag,
                )
            assert diag[0]["fallback_reason"] == FALLBACK_REASON_EXECUTION_ERROR
        finally:
            override_settings(None)

    def test_backend_called_true_on_successful_call(self):
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch("requests.post", return_value=_mock_response('{"k": 1}')):
                run_prompt(
                    prompt_name="narrative",
                    context={"topic": "T", "goal": "", "audience": ""},
                    parser=lambda raw: json.loads(raw),
                    fallback=lambda: "FALLBACK",
                    diagnostics_out=diag,
                )
            assert diag[0]["backend_called"] is True
        finally:
            override_settings(None)

    def test_raw_output_length_recorded(self):
        response_text = '{"key": "value"}'
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch("requests.post", return_value=_mock_response(response_text)):
                run_prompt(
                    prompt_name="narrative",
                    context={"topic": "T", "goal": "", "audience": ""},
                    parser=lambda raw: json.loads(raw),
                    fallback=lambda: "FALLBACK",
                    diagnostics_out=diag,
                )
            assert diag[0]["raw_output_length"] == len(response_text)
        finally:
            override_settings(None)


# ---------------------------------------------------------------------------
# Part 5 — End-to-end through run_prompt() with valid Ollama JSON response
# ---------------------------------------------------------------------------

class TestOllamaEndToEnd:
    def test_valid_narrative_json_parsed_successfully(self):
        """When Ollama returns valid narrative JSON, run_prompt must NOT fall back."""
        narrative_json = json.dumps([
            {"title": "Cloud Cost Problem", "intent_type": "problem", "key_points": ["Costs are high", "ROI unclear", "Budget overspent"]},
            {"title": "Optimisation Strategy", "intent_type": "solution", "key_points": ["Right-size VMs", "Use reserved instances", "Tag governance"]},
            {"title": "Projected Savings", "intent_type": "impact", "key_points": ["30% cost reduction", "Improved unit economics"]},
        ])

        override_settings(_ollama_settings())
        try:
            diag = []
            with patch("requests.post", return_value=_mock_response(narrative_json)):
                from pptgen.content_intelligence.narrative_builder import build_narrative
                from pptgen.content_intelligence.content_models import ContentIntent
                result = build_narrative(ContentIntent(topic="Cloud Cost Optimisation"))
            assert len(result) == 3
            assert result[0].title == "Cloud Cost Problem"
            assert result[0].intent_type == "problem"
        finally:
            override_settings(None)

    def test_narrative_fallback_NOT_used_on_valid_response(self):
        """When Ollama returns valid JSON, the deterministic fallback must not fire."""
        narrative_json = json.dumps([
            {"title": "Real Title", "intent_type": "problem", "key_points": ["Real point"]},
        ])
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch("requests.post", return_value=_mock_response(narrative_json)):
                from pptgen.content_intelligence.narrative_builder import build_narrative
                from pptgen.content_intelligence.content_models import ContentIntent
                result = build_narrative(ContentIntent(topic="Test Topic"))
            # Fallback produces "Key point about problem for Test Topic."
            for slide in result:
                assert not slide.title.startswith("Test Topic: ")
        finally:
            override_settings(None)

    def test_malformed_ollama_response_triggers_fallback(self):
        """If Ollama returns non-JSON, run_prompt must fall back gracefully."""
        override_settings(_ollama_settings())
        try:
            diag = []
            with patch("requests.post", return_value=_mock_response("this is not JSON")):
                from pptgen.content_intelligence.narrative_builder import build_narrative
                from pptgen.content_intelligence.content_models import ContentIntent
                result = build_narrative(ContentIntent(topic="Fallback Topic"))
            # Fallback must still produce a valid list of SlideIntents
            assert isinstance(result, list)
            assert len(result) >= 1
        finally:
            override_settings(None)

    def test_ollama_connection_error_uses_fallback(self):
        import requests as _requests
        override_settings(_ollama_settings())
        try:
            with patch("requests.post", side_effect=_requests.ConnectionError("no server")):
                from pptgen.content_intelligence.narrative_builder import build_narrative
                from pptgen.content_intelligence.content_models import ContentIntent
                result = build_narrative(ContentIntent(topic="Connection Test"))
            assert isinstance(result, list)
            assert len(result) >= 1
        finally:
            override_settings(None)


# ---------------------------------------------------------------------------
# Settings field verification
# ---------------------------------------------------------------------------

class TestOllamaSettings:
    def test_default_ollama_model(self):
        s = RuntimeSettings()
        assert s.ollama_model == "qwen3:latest"

    def test_default_ollama_base_url(self):
        s = RuntimeSettings()
        assert s.ollama_base_url == "http://localhost:11434"

    def test_custom_ollama_model(self):
        s = RuntimeSettings(ollama_model="llama3.2:latest")
        assert s.ollama_model == "llama3.2:latest"

    def test_custom_ollama_base_url(self):
        s = RuntimeSettings(ollama_base_url="http://192.168.1.5:11434")
        assert s.ollama_base_url == "http://192.168.1.5:11434"


# ---------------------------------------------------------------------------
# Ollama retry behaviour
# ---------------------------------------------------------------------------

class TestOllamaRetryBehavior:
    """Verify retry logic in _build_ollama_caller() — transient vs non-retryable."""

    def test_transient_connection_error_then_success_returns_result(self):
        """A single ConnectionError followed by a successful response must succeed."""
        import requests as _requests

        good_response = _mock_response('{"response": "ok"}')
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _requests.ConnectionError("transient failure")
            return _mock_response('{"response": "ok"}')

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        with patch("requests.post", side_effect=_side_effect):
            result = caller("some prompt")

        assert result == '{"response": "ok"}'
        assert call_count == 2

    def test_repeated_connection_error_raises_after_max_attempts(self):
        """Two consecutive ConnectionErrors must propagate after max attempts."""
        import requests as _requests

        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise _requests.ConnectionError("persistent failure")

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        with pytest.raises(_requests.ConnectionError):
            with patch("requests.post", side_effect=_side_effect):
                caller("some prompt")

        assert call_count == 2  # _OLLAMA_MAX_ATTEMPTS

    def test_transient_5xx_then_success_returns_result(self):
        """HTTP 500 on first attempt followed by 200 must succeed."""
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_error_response(500)
            return _mock_response('{"result": "good"}')

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        with patch("requests.post", side_effect=_side_effect):
            result = caller("some prompt")

        assert result == '{"result": "good"}'
        assert call_count == 2

    def test_4xx_error_is_not_retried(self):
        """HTTP 400 must raise immediately without retry."""
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _mock_error_response(400)

        import requests as _requests

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        with pytest.raises(_requests.HTTPError):
            with patch("requests.post", side_effect=_side_effect):
                caller("some prompt")

        assert call_count == 1  # no retry for 4xx

    def test_empty_response_then_success_returns_result(self):
        """Empty response on first attempt then valid response must succeed."""
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                resp = MagicMock()
                resp.status_code = 200
                resp.raise_for_status = MagicMock()
                resp.json.return_value = {"response": "", "done": True}
                return resp
            return _mock_response('{"data": "value"}')

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        with patch("requests.post", side_effect=_side_effect):
            result = caller("some prompt")

        assert result == '{"data": "value"}'
        assert call_count == 2

    def test_repeated_empty_response_raises_after_max_attempts(self):
        """Two consecutive empty responses must raise RuntimeError."""
        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"response": "", "done": True}
            return resp

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        with pytest.raises(RuntimeError, match="empty response"):
            with patch("requests.post", side_effect=_side_effect):
                caller("some prompt")

        assert call_count == 2

    def test_run_prompt_records_execution_error_on_connection_failure(self):
        """run_prompt must record execution_error when Ollama is unreachable."""
        import requests as _requests

        diag = []
        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")

        def _failing_caller(prompt: str) -> str:
            raise _requests.ConnectionError("host unreachable")

        _failing_caller._backend_name = "ollama"

        result = run_prompt(
            prompt_name="narrative",
            context={"topic": "Test", "goal": "", "audience": ""},
            parser=lambda s: s,
            fallback=lambda: "fallback_value",
            llm_caller=_failing_caller,
            diagnostics_out=diag,
        )

        assert result == "fallback_value"
        assert diag[0]["execution_error"] is not None
        assert "ConnectionError" in diag[0]["execution_error"]


# ---------------------------------------------------------------------------
# Enhanced diagnostics
# ---------------------------------------------------------------------------

class TestOllamaEnhancedDiagnostics:
    """Verify prompt_length, execution_error, and caller attribute diagnostics."""

    def test_prompt_length_captured_in_diagnostics(self):
        """run_prompt must record prompt_length after building the prompt."""
        good_json = '[{"title":"T","intent_type":"problem","key_points":["k"]}]'
        diag = []

        def _caller(prompt: str) -> str:
            return good_json

        _caller._backend_name = "test"

        run_prompt(
            prompt_name="narrative",
            context={"topic": "Cloud Cost", "goal": "reduce spend", "audience": "Execs"},
            parser=lambda s: s,
            fallback=lambda: [],
            llm_caller=_caller,
            diagnostics_out=diag,
        )

        assert diag[0]["prompt_length"] is not None
        assert isinstance(diag[0]["prompt_length"], int)
        assert diag[0]["prompt_length"] > 0

    def test_execution_error_none_on_success(self):
        """execution_error must be None when the LLM call succeeds."""
        diag = []

        def _caller(prompt: str) -> str:
            return '{"assertion":"a","supporting_points":["p1","p2","p3"]}'

        _caller._backend_name = "test"

        run_prompt(
            prompt_name="expansion",
            context={"title": "T", "intent_type": "solution", "key_points": ["k"], "topic": "T"},
            parser=lambda s: s,
            fallback=lambda: {},
            llm_caller=_caller,
            diagnostics_out=diag,
        )

        assert diag[0]["execution_error"] is None

    def test_execution_error_captured_with_type_and_message(self):
        """execution_error must contain '<ExcType>: <message>' on failure."""
        diag = []

        def _failing(prompt: str) -> str:
            raise ValueError("something went wrong with the model")

        _failing._backend_name = "test"

        run_prompt(
            prompt_name="narrative",
            context={"topic": "Test", "goal": "", "audience": ""},
            parser=lambda s: s,
            fallback=lambda: "fb",
            llm_caller=_failing,
            diagnostics_out=diag,
        )

        assert diag[0]["execution_error"] is not None
        assert "ValueError" in diag[0]["execution_error"]
        assert "something went wrong" in diag[0]["execution_error"]

    def test_ollama_caller_exposes_backend_name_attribute(self):
        """_build_ollama_caller must set _backend_name='ollama' on the callable."""
        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        assert getattr(caller, "_backend_name", None) == "ollama"

    def test_ollama_caller_exposes_model_attribute(self):
        """_build_ollama_caller must expose _ollama_model attribute."""
        caller = _build_ollama_caller("http://localhost:11434", "llama3.2:latest")
        assert getattr(caller, "_ollama_model", None) == "llama3.2:latest"

    def test_ollama_caller_exposes_base_url_attribute(self):
        """_build_ollama_caller must expose _ollama_base_url attribute."""
        caller = _build_ollama_caller("http://192.168.1.5:11434", "qwen3:latest")
        assert getattr(caller, "_ollama_base_url", None) == "http://192.168.1.5:11434"

    def test_backend_name_appears_in_diagnostics_from_ollama_caller(self):
        """When an Ollama caller is used, diagnostics must record backend='ollama'."""
        good_json = '[{"title":"T","intent_type":"problem","key_points":["k"]}]'
        diag = []

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")

        with patch("requests.post", return_value=_mock_response(good_json)):
            run_prompt(
                prompt_name="narrative",
                context={"topic": "Test", "goal": "", "audience": ""},
                parser=lambda s: s,
                fallback=lambda: [],
                llm_caller=caller,
                diagnostics_out=diag,
            )

        assert diag[0]["backend"] == "ollama"


# ---------------------------------------------------------------------------
# Prompt template sanity — JSON contract preserved after trimming
# ---------------------------------------------------------------------------

class TestPromptTemplateSanity:
    """Verify that trimmed prompt templates still enforce the JSON-only contract."""

    def test_narrative_prompt_contains_json_only_instruction(self):
        from pptgen.content_intelligence.prompts.narrative_prompt import build_prompt
        prompt = build_prompt({"topic": "Cloud Cost", "goal": "Reduce spend", "audience": "Execs"})
        assert "Output ONLY the JSON" in prompt

    def test_narrative_prompt_starts_with_bracket_instruction(self):
        from pptgen.content_intelligence.prompts.narrative_prompt import build_prompt
        prompt = build_prompt({"topic": "Cloud Cost", "goal": "Reduce spend", "audience": "Execs"})
        assert "Start with [" in prompt

    def test_expansion_prompt_contains_json_only_instruction(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({"title": "T", "intent_type": "problem", "key_points": ["k"], "topic": "T"})
        assert "Output ONLY the JSON" in prompt

    def test_expansion_prompt_starts_with_brace_instruction(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({"title": "T", "intent_type": "problem", "key_points": ["k"], "topic": "T"})
        assert "Start with {" in prompt

    def test_insight_prompt_contains_json_only_instruction(self):
        from pptgen.content_intelligence.prompts.insight_prompt import build_prompt
        prompt = build_prompt({"title": "T", "assertion": "A", "supporting_points": ["p"]})
        assert "Output ONLY the JSON" in prompt

    def test_insight_prompt_starts_with_brace_instruction(self):
        from pptgen.content_intelligence.prompts.insight_prompt import build_prompt
        prompt = build_prompt({"title": "T", "assertion": "A", "supporting_points": ["p"]})
        assert "Start with {" in prompt

    def test_narrative_prompt_does_not_contain_role_persona(self):
        """Role persona framing was removed — prompt must not start with 'You are'."""
        from pptgen.content_intelligence.prompts.narrative_prompt import build_prompt
        prompt = build_prompt({"topic": "T", "goal": "G", "audience": "A"})
        assert not prompt.startswith("You are")

    def test_expansion_prompt_does_not_contain_role_persona(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({"title": "T", "intent_type": "problem", "key_points": [], "topic": "T"})
        assert not prompt.startswith("You are")

    def test_insight_prompt_does_not_contain_role_persona(self):
        from pptgen.content_intelligence.prompts.insight_prompt import build_prompt
        prompt = build_prompt({"title": "T", "assertion": "A", "supporting_points": []})
        assert not prompt.startswith("You are")

    def test_narrative_prompt_under_1000_chars(self):
        """Trimmed narrative prompt must be concise — under 1000 chars for typical inputs."""
        from pptgen.content_intelligence.prompts.narrative_prompt import build_prompt
        prompt = build_prompt({"topic": "Cloud Cost", "goal": "Reduce spend", "audience": "Execs"})
        assert len(prompt) < 1000, f"Narrative prompt is {len(prompt)} chars — too verbose"

    def test_expansion_prompt_under_800_chars(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({"title": "T", "intent_type": "problem", "key_points": ["kp1"], "topic": "T"})
        assert len(prompt) < 800, f"Expansion prompt is {len(prompt)} chars — too verbose"

    def test_insight_prompt_under_700_chars(self):
        from pptgen.content_intelligence.prompts.insight_prompt import build_prompt
        prompt = build_prompt({"title": "T", "assertion": "A", "supporting_points": ["p"]})
        assert len(prompt) < 700, f"Insight prompt is {len(prompt)} chars — too verbose"


# ---------------------------------------------------------------------------
# Ollama timeout setting
# ---------------------------------------------------------------------------

class TestOllamaTimeoutSetting:
    """ollama_timeout_seconds — default, env override, and wiring."""

    def test_default_ollama_timeout_is_120(self):
        from pptgen.config import RuntimeSettings
        s = RuntimeSettings()
        assert s.ollama_timeout_seconds == 120

    def test_ollama_timeout_env_override(self, monkeypatch):
        import importlib
        monkeypatch.setenv("PPTGEN_OLLAMA_TIMEOUT", "180")
        from pptgen.config import RuntimeSettings
        s = RuntimeSettings.from_env()
        assert s.ollama_timeout_seconds == 180

    def test_ollama_timeout_wired_to_caller_attribute(self):
        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest", timeout=90)
        assert getattr(caller, "_ollama_timeout_seconds", None) == 90

    def test_ollama_caller_uses_configured_timeout(self):
        """requests.post must be called with the caller's configured timeout."""
        captured: list[int] = []

        def _side_effect(*args, **kwargs):
            captured.append(kwargs.get("timeout"))
            return _mock_response('{"result": "ok"}')

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest", timeout=90)
        with patch("requests.post", side_effect=_side_effect):
            caller("some prompt")

        assert captured[0] == 90

    def test_make_default_caller_passes_timeout_from_settings(self):
        """_make_default_caller must wire ollama_timeout_seconds into the caller."""
        override_settings(_ollama_settings(ollama_timeout_seconds=150))
        try:
            caller = _make_default_caller()
            assert getattr(caller, "_ollama_timeout_seconds", None) == 150
        finally:
            override_settings(None)

    def test_max_attempts_attribute_present(self):
        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        assert getattr(caller, "_ollama_max_attempts", None) == 2


# ---------------------------------------------------------------------------
# Timeout diagnostics
# ---------------------------------------------------------------------------

class TestTimeoutDiagnostics:
    """Verify is_timeout classification and timeout_seconds in diagnostics."""

    def test_timeout_failure_sets_is_timeout_true(self):
        """ReadTimeout must set is_timeout=True in diagnostics."""
        import requests as _requests

        diag = []

        def _timing_out(prompt: str) -> str:
            raise _requests.ReadTimeout("read timeout=120")

        _timing_out._backend_name = "ollama"
        _timing_out._ollama_model = "qwen3:latest"
        _timing_out._ollama_timeout_seconds = 120
        _timing_out._ollama_max_attempts = 2

        run_prompt(
            prompt_name="narrative",
            context={"topic": "Test", "goal": "", "audience": ""},
            parser=lambda s: s,
            fallback=lambda: "fb",
            llm_caller=_timing_out,
            diagnostics_out=diag,
        )

        assert diag[0]["is_timeout"] is True

    def test_connection_error_sets_is_timeout_false(self):
        """ConnectionError is not a timeout and must not set is_timeout=True."""
        import requests as _requests

        diag = []

        def _failing(prompt: str) -> str:
            raise _requests.ConnectionError("host unreachable")

        _failing._backend_name = "ollama"

        run_prompt(
            prompt_name="narrative",
            context={"topic": "Test", "goal": "", "audience": ""},
            parser=lambda s: s,
            fallback=lambda: "fb",
            llm_caller=_failing,
            diagnostics_out=diag,
        )

        assert diag[0]["is_timeout"] is False

    def test_success_path_is_timeout_false(self):
        """Successful call must leave is_timeout=False."""
        diag = []

        def _ok(prompt: str) -> str:
            return '[{"title":"T","intent_type":"problem","key_points":["k"]}]'

        _ok._backend_name = "test"

        run_prompt(
            prompt_name="narrative",
            context={"topic": "T", "goal": "", "audience": ""},
            parser=lambda s: s,
            fallback=lambda: [],
            llm_caller=_ok,
            diagnostics_out=diag,
        )

        assert diag[0]["is_timeout"] is False

    def test_timeout_seconds_populated_from_caller_attribute(self):
        """timeout_seconds in diagnostics must reflect the caller's configured value."""
        import requests as _requests

        diag = []
        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest", timeout=90)

        with patch("requests.post", side_effect=_requests.ReadTimeout("timed out")):
            run_prompt(
                prompt_name="narrative",
                context={"topic": "Test", "goal": "", "audience": ""},
                parser=lambda s: s,
                fallback=lambda: "fb",
                llm_caller=caller,
                diagnostics_out=diag,
            )

        assert diag[0]["timeout_seconds"] == 90

    def test_ollama_model_populated_in_diagnostics(self):
        """ollama_model in diagnostics must reflect the caller's model tag."""
        diag = []
        caller = _build_ollama_caller("http://localhost:11434", "llama3.2:latest", timeout=120)
        good_json = '[{"title":"T","intent_type":"problem","key_points":["k"]}]'

        with patch("requests.post", return_value=_mock_response(good_json)):
            run_prompt(
                prompt_name="narrative",
                context={"topic": "T", "goal": "", "audience": ""},
                parser=lambda s: s,
                fallback=lambda: [],
                llm_caller=caller,
                diagnostics_out=diag,
            )

        assert diag[0]["ollama_model"] == "llama3.2:latest"

    def test_retry_attempted_true_for_ollama_caller(self):
        """retry_attempted must be True for an Ollama caller (max_attempts=2)."""
        diag = []
        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest")
        good_json = '{"assertion":"a","supporting_points":["p1","p2","p3"]}'

        with patch("requests.post", return_value=_mock_response(good_json)):
            run_prompt(
                prompt_name="expansion",
                context={"title":"T","intent_type":"impact","key_points":[],"topic":"T"},
                parser=lambda s: s,
                fallback=lambda: {},
                llm_caller=caller,
                diagnostics_out=diag,
            )

        assert diag[0]["retry_attempted"] is True

    def test_retry_attempted_false_for_non_ollama_caller(self):
        """retry_attempted must be False when the caller has no _ollama_max_attempts."""
        diag = []

        def _simple(prompt: str) -> str:
            return '{"assertion":"a","supporting_points":["p1","p2","p3"]}'

        _simple._backend_name = "anthropic"
        # no _ollama_max_attempts attribute

        run_prompt(
            prompt_name="expansion",
            context={"title":"T","intent_type":"solution","key_points":[],"topic":"T"},
            parser=lambda s: s,
            fallback=lambda: {},
            llm_caller=_simple,
            diagnostics_out=diag,
        )

        assert diag[0]["retry_attempted"] is False

    def test_timeout_fallback_still_returns_valid_result(self):
        """Even on ReadTimeout, fallback must produce a usable result."""
        import requests as _requests

        caller = _build_ollama_caller("http://localhost:11434", "qwen3:latest", timeout=120)

        with patch("requests.post", side_effect=_requests.ReadTimeout("timed out")):
            result = run_prompt(
                prompt_name="narrative",
                context={"topic": "Test", "goal": "", "audience": ""},
                parser=lambda s: s,
                fallback=lambda: "deterministic_fallback",
                llm_caller=caller,
            )

        assert result == "deterministic_fallback"


# ---------------------------------------------------------------------------
# Expansion prompt — impact/metrics quality framing
# ---------------------------------------------------------------------------

class TestExpansionPromptIntentGuidance:
    """Verify intent_guidance injection for impact and metrics slide types."""

    def test_impact_intent_injects_guidance(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Cost Overrun Impact",
            "intent_type": "impact",
            "key_points": ["Costs up 40%"],
            "topic": "Cost Overrun Impact",
        })
        assert "financial exposure" in prompt or "business consequences" in prompt

    def test_metrics_intent_injects_guidance(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Platform Metrics",
            "intent_type": "metrics",
            "key_points": ["99.5% uptime"],
            "topic": "Platform Metrics",
        })
        assert "measurable" in prompt or "KPI" in prompt or "benchmark" in prompt

    def test_problem_intent_no_guidance(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Root Cause",
            "intent_type": "problem",
            "key_points": ["latency spike"],
            "topic": "Root Cause",
        })
        # Generic intent types must not inject business-consequence framing
        assert "financial exposure" not in prompt
        assert "measurable outcomes" not in prompt

    def test_solution_intent_no_guidance(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Proposed Fix",
            "intent_type": "solution",
            "key_points": ["new approach"],
            "topic": "Proposed Fix",
        })
        assert "financial exposure" not in prompt

    def test_empty_intent_no_guidance(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({"title": "T", "intent_type": "", "key_points": [], "topic": "T"})
        assert "Focus:" not in prompt

    def test_impact_prompt_json_contract_preserved(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Impact Slide",
            "intent_type": "impact",
            "key_points": ["item"],
            "topic": "Impact Slide",
        })
        assert "Output ONLY the JSON" in prompt
        assert "Start with {" in prompt

    def test_metrics_prompt_json_contract_preserved(self):
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Metrics Slide",
            "intent_type": "metrics",
            "key_points": ["item"],
            "topic": "Metrics Slide",
        })
        assert "Output ONLY the JSON" in prompt
        assert "assertion" in prompt
        assert "supporting_points" in prompt

    def test_impact_prompt_not_larger_than_1000_chars(self):
        """Impact prompt with guidance must still be compact."""
        from pptgen.content_intelligence.prompts.expansion_prompt import build_prompt
        prompt = build_prompt({
            "title": "Cost Overrun",
            "intent_type": "impact",
            "key_points": ["Costs up", "Revenue down"],
            "topic": "Cost Overrun",
        })
        assert len(prompt) < 1000, f"Impact expansion prompt is {len(prompt)} chars"
