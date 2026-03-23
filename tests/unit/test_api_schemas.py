"""Unit tests for API request/response schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pptgen.api.schemas import (
    ErrorResponse,
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    PlaybooksResponse,
    TemplatesResponse,
)


class TestGenerateRequest:
    def test_defaults(self):
        req = GenerateRequest(text="hello")
        assert req.text == "hello"
        assert req.mode == "deterministic"
        assert req.template_id is None
        assert req.artifacts is False
        assert req.preview_only is False

    def test_ai_mode(self):
        req = GenerateRequest(text="x", mode="ai")
        assert req.mode == "ai"

    def test_template_id(self):
        req = GenerateRequest(text="x", template_id="ops_review_v1")
        assert req.template_id == "ops_review_v1"

    def test_artifacts_true(self):
        req = GenerateRequest(text="x", artifacts=True)
        assert req.artifacts is True

    def test_preview_only_true(self):
        req = GenerateRequest(text="x", preview_only=True)
        assert req.preview_only is True

    def test_missing_text_raises(self):
        with pytest.raises(ValidationError):
            GenerateRequest()

    def test_full_request(self):
        req = GenerateRequest(
            text="sprint backlog",
            mode="ai",
            template_id="ops_review_v1",
            artifacts=True,
            preview_only=False,
        )
        assert req.mode == "ai"
        assert req.template_id == "ops_review_v1"


class TestHealthResponse:
    def test_ok_status(self):
        r = HealthResponse(request_id="abc", status="ok")
        assert r.status == "ok"

    def test_serializes(self):
        r = HealthResponse(request_id="abc", status="ok")
        assert r.model_dump() == {"request_id": "abc", "status": "ok"}

    def test_request_id_field(self):
        r = HealthResponse(request_id="abc", status="ok")
        assert r.request_id == "abc"


class TestTemplatesResponse:
    def test_empty(self):
        r = TemplatesResponse(request_id="x", templates=[])
        assert r.templates == []

    def test_with_items(self):
        r = TemplatesResponse(request_id="x", templates=["a", "b"])
        assert len(r.templates) == 2

    def test_missing_templates_raises(self):
        with pytest.raises(ValidationError):
            TemplatesResponse()

    def test_request_id_field(self):
        r = TemplatesResponse(request_id="x", templates=[])
        assert r.request_id == "x"


class TestPlaybooksResponse:
    def test_with_items(self):
        r = PlaybooksResponse(request_id="x", playbooks=["p1", "p2"])
        assert r.playbooks == ["p1", "p2"]

    def test_request_id_field(self):
        r = PlaybooksResponse(request_id="x", playbooks=[])
        assert r.request_id == "x"


class TestGenerateResponse:
    def test_minimal(self):
        r = GenerateResponse(
            request_id="abc",
            success=True,
            playbook_id="meeting-notes-to-eos-rocks",
            mode="deterministic",
            stage="rendered",
        )
        assert r.success is True
        assert r.slide_count is None
        assert r.output_path is None

    def test_full(self):
        r = GenerateResponse(
            request_id="abc",
            success=True,
            playbook_id="ado-summary-to-weekly-delivery",
            template_id="ops_review_v1",
            mode="ai",
            stage="rendered",
            slide_count=5,
            slide_types=["title", "bullets"],
            output_path="/tmp/out.pptx",
            artifact_paths={"spec": "/tmp/spec.json"},
            notes="some note",
        )
        assert r.slide_count == 5
        assert r.artifact_paths == {"spec": "/tmp/spec.json"}

    def test_failed_response(self):
        r = GenerateResponse(
            request_id="abc",
            success=False,
            playbook_id="generic-summary-playbook",
            mode="deterministic",
            stage="failed",
        )
        assert r.success is False

    def test_request_id_field(self):
        r = GenerateResponse(
            request_id="abc",
            success=True,
            playbook_id="x",
            mode="deterministic",
            stage="rendered",
        )
        assert r.request_id == "abc"


class TestErrorResponse:
    def test_error_field(self):
        e = ErrorResponse(request_id="abc", error="something went wrong")
        assert e.error == "something went wrong"

    def test_request_id_field(self):
        e = ErrorResponse(request_id="abc", error="something went wrong")
        assert e.request_id == "abc"
