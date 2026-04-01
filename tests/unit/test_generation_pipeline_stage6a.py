"""Stage 6A tests for generation_pipeline — RunContext wiring and input size guard."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pptgen.config import RuntimeSettings, override_settings
from pptgen.errors import InputSizeError
from pptgen.pipeline import PipelineError, generate_presentation
from pptgen.runtime import RunContext


# ---------------------------------------------------------------------------
# Input size guard
# ---------------------------------------------------------------------------

class TestInputSizeGuard:
    def test_input_over_max_bytes_raises_input_size_error(self):
        override_settings(RuntimeSettings(max_input_bytes=10))
        try:
            with pytest.raises(InputSizeError, match="exceeds maximum size"):
                generate_presentation("This text is definitely longer than ten bytes.")
        finally:
            override_settings(None)

    def test_input_at_limit_does_not_raise(self):
        # Exactly at the limit should pass (guard is >, not >=)
        text = "a" * 10
        override_settings(RuntimeSettings(max_input_bytes=10))
        try:
            # May raise PipelineError for routing, but NOT InputSizeError
            try:
                generate_presentation(text)
            except PipelineError:
                pass
            # If we get here without InputSizeError, the guard passed
        finally:
            override_settings(None)

    def test_empty_input_not_blocked_by_size_guard(self):
        override_settings(RuntimeSettings(max_input_bytes=10))
        try:
            # Empty string → 0 bytes, should not be blocked by size guard
            try:
                generate_presentation("")
            except PipelineError:
                pass  # routing failure is fine; we only care it's not InputSizeError
        finally:
            override_settings(None)

    def test_normal_input_not_blocked(self):
        text = "Meeting notes. Attendees: Alice. Action items and follow-up decisions."
        # Default max_input_bytes is 512 KB — this text is trivially small
        result = generate_presentation(text)
        assert result.playbook_id is not None


# ---------------------------------------------------------------------------
# RunContext wiring
# ---------------------------------------------------------------------------

class TestRunContextWiring:
    def test_run_context_accepted_as_optional_param(self):
        ctx = RunContext()
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
            run_context=ctx,
        )
        assert result.playbook_id is not None

    def test_run_context_playbook_id_populated(self):
        ctx = RunContext()
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
            run_context=ctx,
        )
        assert ctx.playbook_id == result.playbook_id

    def test_run_context_stage_timings_populated(self):
        ctx = RunContext()
        generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
            run_context=ctx,
        )
        stage_names = [t.stage for t in ctx.timings]
        assert "route_input" in stage_names
        assert "execute_playbook" in stage_names
        assert "plan_slides" in stage_names
        assert "convert_spec" in stage_names

    def test_run_context_all_stages_completed(self):
        ctx = RunContext()
        generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
            run_context=ctx,
        )
        for timer in ctx.timings:
            assert timer.ended_at is not None, f"Stage '{timer.stage}' was not ended"

    def test_run_context_total_ms_positive(self):
        ctx = RunContext()
        generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
            run_context=ctx,
        )
        assert ctx.total_ms() > 0

    def test_no_run_context_is_backward_compatible(self):
        # Passing no run_context should work exactly as before
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions."
        )
        assert result.playbook_id is not None

    def test_none_run_context_is_backward_compatible(self):
        result = generate_presentation(
            "Meeting notes. Attendees: Alice. Action items and follow-up decisions.",
            run_context=None,
        )
        assert result.playbook_id is not None
