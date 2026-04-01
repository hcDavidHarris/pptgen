"""Explicit backward compatibility regression tests for Stage 6B.

These tests assert that all Stage 6A-visible behavior is unchanged after
Stage 6B changes are applied.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app
from pptgen.pipeline import generate_presentation
from pptgen.pipeline.generation_pipeline import PipelineResult

_MEETING_TEXT = "Meeting notes. Attendees: Alice. Action items and follow-up decisions."


class TestSyncApiBackwardCompat:
    """POST /v1/generate must behave identically to pre-Stage-6B."""

    def test_generate_endpoint_returns_200(self):
        client = TestClient(app)
        resp = client.post("/v1/generate", json={"text": _MEETING_TEXT})
        assert resp.status_code == 200

    def test_generate_response_has_success_field(self):
        client = TestClient(app)
        resp = client.post("/v1/generate", json={"text": _MEETING_TEXT})
        assert resp.json()["success"] is True

    def test_generate_response_has_run_id(self):
        client = TestClient(app)
        resp = client.post("/v1/generate", json={"text": _MEETING_TEXT})
        assert resp.json().get("run_id") is not None

    def test_generate_response_has_playbook_id(self):
        client = TestClient(app)
        resp = client.post("/v1/generate", json={"text": _MEETING_TEXT})
        assert resp.json().get("playbook_id") is not None


class TestPipelineBackwardCompat:
    """generate_presentation() must work with zero new arguments."""

    def test_no_run_context_works(self):
        result = generate_presentation(_MEETING_TEXT)
        assert isinstance(result, PipelineResult)
        assert result.playbook_id is not None

    def test_none_run_context_works(self):
        result = generate_presentation(_MEETING_TEXT, run_context=None)
        assert result.playbook_id is not None

    def test_generate_returns_pipeline_result(self):
        result = generate_presentation(_MEETING_TEXT)
        assert hasattr(result, "playbook_id")
        assert hasattr(result, "template_id")
        assert hasattr(result, "stage")


class TestMetaEndpointsBackwardCompat:
    """Meta endpoints must continue to respond correctly."""

    def test_health_check(self):
        client = TestClient(app)
        resp = client.get("/v1/health")
        assert resp.status_code == 200

    def test_list_templates(self):
        client = TestClient(app)
        resp = client.get("/v1/templates")
        assert resp.status_code == 200
        assert "templates" in resp.json()

    def test_list_playbooks(self):
        client = TestClient(app)
        resp = client.get("/v1/playbooks")
        assert resp.status_code == 200
        assert "playbooks" in resp.json()
