"""Tests verifying that the sync API path correctly populates run metadata.

Before the fix in service.py, `generate_presentation()` was called without
`run_context=ctx`, so stage timings were never recorded and `ctx.total_ms()`
always returned 0.0.  These tests confirm the fix by calling `run_generate()`
directly and inspecting the returned RunContext.
"""

from __future__ import annotations

import pytest

from pptgen.api.service import run_generate
from pptgen.runtime import RunContext

_TEXT = "Meeting notes. Attendees: Alice. Action: review the plan."


class TestSyncRunMetadata:
    def test_run_context_returned(self):
        _result, ctx = run_generate(
            text=_TEXT,
            mode="deterministic",
            template_id=None,
            artifacts=False,
            preview_only=False,
        )
        assert isinstance(ctx, RunContext)

    def test_total_ms_positive(self):
        _result, ctx = run_generate(
            text=_TEXT,
            mode="deterministic",
            template_id=None,
            artifacts=False,
            preview_only=False,
        )
        assert ctx.total_ms() > 0, (
            "total_ms() returned 0 — run_context was not passed to generate_presentation()"
        )

    def test_stage_timings_populated(self):
        _result, ctx = run_generate(
            text=_TEXT,
            mode="deterministic",
            template_id=None,
            artifacts=False,
            preview_only=False,
        )
        timings = ctx.as_dict().get("timings", [])
        assert len(timings) > 0, "No stage timings recorded"

    def test_playbook_id_set_on_context(self):
        _result, ctx = run_generate(
            text=_TEXT,
            mode="deterministic",
            template_id=None,
            artifacts=False,
            preview_only=False,
        )
        assert ctx.playbook_id is not None, (
            "playbook_id not set on RunContext — run_context was not passed to generate_presentation()"
        )

    def test_run_id_is_uuid(self):
        import uuid as _uuid
        _result, ctx = run_generate(
            text=_TEXT,
            mode="deterministic",
            template_id=None,
            artifacts=False,
            preview_only=False,
        )
        # Should parse without raising
        _uuid.UUID(ctx.run_id)
