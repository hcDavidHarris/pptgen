"""Prompt runner — Phase 11B execution layer.

Provides a single function, ``run_prompt()``, that:

  1. Builds a prompt via the registry (prompt_name + context → str).
  2. Executes the prompt via an LLM caller (str → str).
  3. Strips code fences and parses the response (str → T).
  4. Validates the parsed result (T → bool).
  5. Returns the valid result, or the deterministic fallback on any failure.

Design rules
------------
- No global state.
- No hidden side effects.
- No retries beyond a single attempt.
- Fully injectable for testing via the ``llm_caller`` parameter.
- The fallback is ALWAYS deterministic and ALWAYS has the same output schema.
- Partial or invalid results NEVER propagate — it is all-or-nothing.

Observability
-------------
``run_prompt`` emits a WARNING-level log whenever fallback is triggered.
Each log line includes the prompt name, fallback reason, and backend identity
so that silent fallback is never ambiguous.

Pass ``diagnostics_out=[]`` to collect a structured diagnostic dict per call:

    diag = []
    result = run_prompt(..., diagnostics_out=diag)
    # diag[0] has: prompt_name, backend, fallback_used, fallback_reason,
    #              backend_called, raw_output_length, prompt_length,
    #              parse_succeeded, validation_succeeded,
    #              execution_error, is_timeout,
    #              ollama_model, timeout_seconds, retry_attempted
"""
from __future__ import annotations

import logging
import re
from typing import Callable, TypeVar

from .prompts.prompt_registry import get_prompt

_logger = logging.getLogger(__name__)

T = TypeVar("T")

# Strips optional ```json ... ``` or ``` ... ``` markdown code fences.
_CODE_FENCE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)
# Strips <think>...</think> reasoning blocks emitted by qwen3 and similar models.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# ---------------------------------------------------------------------------
# Fallback reason constants — import these in tests for explicit assertions.
# ---------------------------------------------------------------------------

#: Prompt succeeded; fallback was not used.
FALLBACK_REASON_NONE = "none"
#: Prompt template could not be built (registry miss or template error).
FALLBACK_REASON_BUILD_ERROR = "build_error"
#: No LLM is configured — model_provider is unset/mock or api_key is empty.
FALLBACK_REASON_NO_LLM = "no_llm"
#: LLM was called but raised an exception (network error, API error, etc.).
FALLBACK_REASON_EXECUTION_ERROR = "execution_error"
#: LLM returned output, but the parser raised (malformed JSON, missing keys).
FALLBACK_REASON_PARSE_ERROR = "parse_error"
#: Parser succeeded, but the validator rejected the result.
FALLBACK_REASON_VALIDATION_FAILURE = "validation_failure"


def extract_json(raw: str) -> str:
    """Extract a JSON string from a raw LLM response.

    Processing order:

    1. Strip ``<think>...</think>`` reasoning blocks (qwen3 and similar
       reasoning models emit these before the JSON payload).
    2. Strip optional triple-backtick code fences (````` ```json ``` `````).
    3. If the result still does not start with ``[`` or ``{``, scan forward
       for the first such character.  This handles models that prepend a
       brief prose sentence before the JSON despite being instructed not to.

    Args:
        raw: Raw string from the LLM.

    Returns:
        JSON string ready for ``json.loads()``.
    """
    # Step 1 — remove <think>...</think> blocks
    cleaned = _THINK_BLOCK.sub("", raw).strip()

    # Step 2 — strip code fences
    match = _CODE_FENCE.match(cleaned)
    if match:
        return match.group(1).strip()

    # Step 3 — scan for first JSON start character when prose precedes the JSON
    if cleaned and cleaned[0] not in ("[", "{"):
        for i, ch in enumerate(cleaned):
            if ch in ("[", "{"):
                close = "]" if ch == "[" else "}"
                candidate = cleaned[i:]
                if close in candidate:
                    return candidate
                break

    return cleaned


def run_prompt(
    prompt_name: str,
    context: dict,
    parser: Callable[[str], T],
    fallback: Callable[[], T],
    validator: Callable[[T], bool] | None = None,
    llm_caller: Callable[[str], str] | None = None,
    diagnostics_out: list[dict] | None = None,
) -> T:
    """Execute a named prompt with structured output, validation, and fallback.

    Execution steps (each failure triggers fallback immediately):

    1. Resolve prompt text via the registry.
    2. Call the LLM (or *llm_caller* if supplied).
    3. Strip code fences and parse the raw response with *parser*.
    4. Validate the parsed result with *validator* (if provided).
    5. Return the valid result, or ``fallback()`` output.

    The fallback is never None — callers must supply a deterministic callable.
    Partial or malformed outputs are never returned; every call is either
    fully valid or fully replaced by the fallback.

    A WARNING is logged and a diagnostic dict appended to *diagnostics_out*
    (when provided) whenever the fallback path is taken.

    Args:
        prompt_name:     Registry key for the prompt (e.g. ``"narrative"``).
        context:         Variables interpolated into the prompt template.
        parser:          Converts the raw LLM response string to type ``T``.
                         Must raise on malformed input.
        fallback:        Returns a deterministic ``T`` on any failure.
        validator:       Optional ``T -> bool``; returning ``False`` triggers fallback.
        llm_caller:      Optional override for LLM execution (``str -> str``).
                         When ``None``, the internal default caller is used, which
                         reads ``PPTGEN_MODEL_PROVIDER`` / ``PPTGEN_MODEL_API_KEY``
                         from settings and falls back immediately if not configured.
        diagnostics_out: Optional list; a diagnostic dict is appended for each
                         call.  Pass an empty list to collect diagnostics without
                         altering behaviour.  The dict always contains the keys
                         documented in the module docstring.

    Returns:
        Parsed and validated ``T``, or ``fallback()`` output.
    """
    caller = llm_caller if llm_caller is not None else _make_default_caller()
    # Detect the stub backend upfront so the fallback reason is precise rather
    # than being silently buried inside a generic execution_error.
    _backend_name = (
        "no_llm_configured"
        if caller is _no_llm_configured
        else getattr(caller, "_backend_name", "configured")
    )

    _diag: dict = {
        "prompt_name": prompt_name,
        "backend": _backend_name,
        "backend_called": False,
        "fallback_used": False,
        "fallback_reason": FALLBACK_REASON_NONE,
        "raw_output_length": None,
        "prompt_length": None,        # chars in rendered prompt — set after build
        "execution_error": None,      # "<ExcType>: <msg>" on execution failure
        "is_timeout": False,          # True when execution_error is a network timeout
        "parse_succeeded": None,
        "validation_succeeded": None,
        # Ollama-specific observability — populated when caller exposes attributes
        "ollama_model": getattr(caller, "_ollama_model", None),
        "timeout_seconds": getattr(caller, "_ollama_timeout_seconds", None),
        "retry_attempted": (getattr(caller, "_ollama_max_attempts", 1) > 1),
    }

    def _trigger_fallback(reason: str) -> T:
        _diag["fallback_used"] = True
        _diag["fallback_reason"] = reason
        _logger.warning(
            "run_prompt(%s): fallback triggered — reason=%s backend=%s",
            prompt_name,
            reason,
            _backend_name,
        )
        if diagnostics_out is not None:
            diagnostics_out.append(_diag)
        return fallback()

    # Step 1 — build prompt
    try:
        prompt = get_prompt(prompt_name, context)
    except Exception:
        return _trigger_fallback(FALLBACK_REASON_BUILD_ERROR)

    _diag["prompt_length"] = len(prompt)

    # Step 2 — execute.
    # Fast-fail with a precise reason when no LLM is wired in, rather than
    # letting _no_llm_configured raise and be caught as a generic error.
    if caller is _no_llm_configured:
        return _trigger_fallback(FALLBACK_REASON_NO_LLM)

    _diag["backend_called"] = True
    try:
        raw = caller(prompt)
        _diag["raw_output_length"] = len(raw)
    except Exception as exc:
        exc_type = type(exc).__name__
        _diag["execution_error"] = f"{exc_type}: {exc}"
        # Classify timeout vs other failure for targeted diagnosis.
        _diag["is_timeout"] = exc_type in ("ReadTimeout", "ConnectTimeout", "Timeout")
        return _trigger_fallback(FALLBACK_REASON_EXECUTION_ERROR)

    # Step 3 — parse (extract_json strips fences before parsing)
    try:
        result = parser(extract_json(raw))
        _diag["parse_succeeded"] = True
    except Exception:
        _diag["parse_succeeded"] = False
        return _trigger_fallback(FALLBACK_REASON_PARSE_ERROR)

    # Step 4 — validate
    if validator is not None:
        try:
            valid = validator(result)
        except Exception:
            valid = False
        _diag["validation_succeeded"] = valid
        if not valid:
            return _trigger_fallback(FALLBACK_REASON_VALIDATION_FAILURE)
    else:
        _diag["validation_succeeded"] = None  # no validator — not applicable

    # Success path
    if diagnostics_out is not None:
        diagnostics_out.append(_diag)
    return result


# ---------------------------------------------------------------------------
# Default LLM caller — provider resolution
# ---------------------------------------------------------------------------

def _make_default_caller() -> Callable[[str], str]:
    """Return the configured LLM caller, or a no-op raiser when unconfigured.

    Provider resolution order:
    1. ``anthropic`` — requires ``model_api_key``.
    2. ``ollama``    — uses a local Ollama HTTP server; no key needed.
    3. anything else → ``_no_llm_configured`` (fallback immediately).

    A no-op raiser causes ``run_prompt`` to fall back immediately, which is
    the correct behaviour when no provider is set up (e.g. in tests or local
    development without an API key).
    """
    try:
        from pptgen.config import get_settings
        settings = get_settings()
    except Exception:
        return _no_llm_configured

    if settings.model_provider == "anthropic" and settings.model_api_key:
        return _build_anthropic_caller(
            api_key=settings.model_api_key,
            model=settings.model_name or "claude-sonnet-4-6",
        )

    if settings.model_provider == "ollama":
        return _build_ollama_caller(
            base_url=settings.ollama_base_url or "http://localhost:11434",
            model=settings.ollama_model or "qwen3:latest",
            timeout=getattr(settings, "ollama_timeout_seconds", 120),
        )

    return _no_llm_configured


def _no_llm_configured(prompt: str) -> str:  # noqa: ARG001
    raise RuntimeError(
        "No LLM configured for prompt runner — using fallback. "
        "Set PPTGEN_MODEL_PROVIDER=anthropic and PPTGEN_MODEL_API_KEY to enable. "
        "Or set PPTGEN_MODEL_PROVIDER=ollama for a local Ollama instance."
    )


def _build_anthropic_caller(api_key: str, model: str) -> Callable[[str], str]:
    """Return a caller that invokes the Anthropic Messages API."""

    def _call(prompt: str) -> str:
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is not installed. "
                "Run: pip install anthropic"
            ) from exc

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    _call._backend_name = "anthropic"  # type: ignore[attr-defined]
    return _call


_OLLAMA_MAX_ATTEMPTS = 2


def _build_ollama_caller(
    base_url: str,
    model: str,
    timeout: int = 120,
) -> Callable[[str], str]:
    """Return a caller that invokes a local Ollama instance via its HTTP API.

    The caller posts to ``{base_url}/api/generate`` with ``stream=false`` and
    returns the ``response`` field from the JSON body.

    Retry policy (transient failures only):
    - Up to ``_OLLAMA_MAX_ATTEMPTS`` total attempts (default: 2).
    - Retried: ``ConnectionError``, ``Timeout``, HTTP 5xx, empty response.
    - Not retried: HTTP 4xx, ``ImportError`` (configuration error).
    - On final failure the exception propagates so ``run_prompt`` records
      ``FALLBACK_REASON_EXECUTION_ERROR`` as usual.

    Diagnostics attributes (accessible via ``getattr``):
    - ``_backend_name``:          ``"ollama"``
    - ``_ollama_model``:          model tag used
    - ``_ollama_base_url``:       server base URL
    - ``_ollama_timeout_seconds``: HTTP request timeout in seconds
    - ``_ollama_max_attempts``:   total attempts allowed (for retry_attempted flag)

    Args:
        base_url: Ollama server base URL (e.g. ``"http://localhost:11434"``).
        model:    Ollama model tag (e.g. ``"qwen3:latest"``).
        timeout:  HTTP request timeout in seconds (default: 120).
    """

    def _call(prompt: str) -> str:
        try:
            import requests  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "The 'requests' package is not installed. "
                "Run: pip install requests"
            ) from exc

        for attempt in range(_OLLAMA_MAX_ATTEMPTS):
            try:
                response = requests.post(
                    f"{base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=timeout,
                )
                response.raise_for_status()
                data = response.json()
                output = data.get("response", "")
                if not output:
                    raise RuntimeError(
                        f"Ollama returned an empty response for model '{model}'. "
                        "Check that the model is pulled and the server is running."
                    )
                return output.strip()

            except requests.HTTPError as exc:
                status = exc.response.status_code if exc.response is not None else 0
                if status >= 500:
                    # 5xx is transient — retry once
                    _logger.warning(
                        "Ollama HTTP %s on attempt %d/%d (model=%s base_url=%s): %s",
                        status, attempt + 1, _OLLAMA_MAX_ATTEMPTS, model, base_url, exc,
                    )
                    if attempt < _OLLAMA_MAX_ATTEMPTS - 1:
                        continue
                raise  # 4xx or final 5xx: propagate immediately

            except (requests.ConnectionError, requests.Timeout) as exc:
                _logger.warning(
                    "Ollama %s on attempt %d/%d (model=%s base_url=%s): %s",
                    type(exc).__name__, attempt + 1, _OLLAMA_MAX_ATTEMPTS, model, base_url, exc,
                )
                if attempt < _OLLAMA_MAX_ATTEMPTS - 1:
                    continue
                raise

            except RuntimeError as exc:
                # Covers empty-response RuntimeError — treat as transient
                _logger.warning(
                    "Ollama empty/invalid response on attempt %d/%d (model=%s): %s",
                    attempt + 1, _OLLAMA_MAX_ATTEMPTS, model, exc,
                )
                if attempt < _OLLAMA_MAX_ATTEMPTS - 1:
                    continue
                raise

    _call._backend_name = "ollama"                    # type: ignore[attr-defined]
    _call._ollama_model = model                        # type: ignore[attr-defined]
    _call._ollama_base_url = base_url                  # type: ignore[attr-defined]
    _call._ollama_timeout_seconds = timeout            # type: ignore[attr-defined]
    _call._ollama_max_attempts = _OLLAMA_MAX_ATTEMPTS  # type: ignore[attr-defined]
    return _call
