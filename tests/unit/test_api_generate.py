"""Tests for POST /v1/generate endpoint."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app

client = TestClient(app)

_MEETING_TEXT = "Meeting notes. Attendees: Alice, Bob. Action items: review deliverables."
_ADO_TEXT = "Sprint 12 backlog velocity 38 story points. Three blocked work items."
_ARCH_TEXT = "ADR-007: option A vs B. Decision: event-driven architecture."


def _post(payload: dict) -> dict:
    r = client.post("/v1/generate", json=payload)
    return r


# ---------------------------------------------------------------------------
# Basic success cases
# ---------------------------------------------------------------------------

class TestGenerateBasic:
    def test_returns_200(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.status_code == 200, r.json()

    def test_success_true(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["success"] is True

    def test_playbook_id_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["playbook_id"]

    def test_mode_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["mode"] == "deterministic"

    def test_stage_is_rendered(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["stage"] == "rendered"

    def test_output_path_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["output_path"] is not None

    def test_output_pptx_exists_on_disk(self):
        r = _post({"text": _MEETING_TEXT})
        out = Path(r.json()["output_path"])
        assert out.exists()
        assert out.suffix == ".pptx"

    def test_slide_count_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["slide_count"] is not None
        assert r.json()["slide_count"] >= 1

    def test_slide_types_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert isinstance(r.json()["slide_types"], list)

    def test_template_id_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["template_id"] is not None


# ---------------------------------------------------------------------------
# Playbook routing via API
# ---------------------------------------------------------------------------

class TestGenerateRouting:
    def test_meeting_notes_routes_correctly(self):
        r = _post({"text": _MEETING_TEXT})
        assert r.json()["playbook_id"] == "meeting-notes-to-eos-rocks"

    def test_ado_text_routes_correctly(self):
        r = _post({"text": _ADO_TEXT})
        assert r.json()["playbook_id"] == "ado-summary-to-weekly-delivery"

    def test_architecture_text_routes_correctly(self):
        r = _post({"text": _ARCH_TEXT})
        assert r.json()["playbook_id"] == "architecture-notes-to-adr-deck"


# ---------------------------------------------------------------------------
# AI mode
# ---------------------------------------------------------------------------

class TestGenerateAIMode:
    def test_ai_mode_returns_200(self):
        r = _post({"text": _MEETING_TEXT, "mode": "ai"})
        assert r.status_code == 200, r.json()

    def test_ai_mode_field_in_response(self):
        r = _post({"text": _MEETING_TEXT, "mode": "ai"})
        assert r.json()["mode"] == "ai"

    def test_ai_mode_rendered(self):
        r = _post({"text": _MEETING_TEXT, "mode": "ai"})
        assert r.json()["stage"] == "rendered"

    def test_ai_mode_has_output_path(self):
        r = _post({"text": _MEETING_TEXT, "mode": "ai"})
        assert r.json()["output_path"] is not None


# ---------------------------------------------------------------------------
# Preview-only mode
# ---------------------------------------------------------------------------

class TestGeneratePreviewOnly:
    def test_preview_only_returns_200(self):
        r = _post({"text": _MEETING_TEXT, "preview_only": True})
        assert r.status_code == 200, r.json()

    def test_preview_only_no_output_path(self):
        r = _post({"text": _MEETING_TEXT, "preview_only": True})
        assert r.json()["output_path"] is None

    def test_preview_only_stage_is_deck_planned(self):
        r = _post({"text": _MEETING_TEXT, "preview_only": True})
        assert r.json()["stage"] == "deck_planned"

    def test_preview_only_slide_count_present(self):
        r = _post({"text": _MEETING_TEXT, "preview_only": True})
        assert r.json()["slide_count"] is not None

    def test_preview_only_ai_mode(self):
        r = _post({"text": _MEETING_TEXT, "mode": "ai", "preview_only": True})
        assert r.status_code == 200
        assert r.json()["output_path"] is None

    def test_preview_only_playbook_id_present(self):
        r = _post({"text": _ADO_TEXT, "preview_only": True})
        assert r.json()["playbook_id"] == "ado-summary-to-weekly-delivery"


# ---------------------------------------------------------------------------
# Template override
# ---------------------------------------------------------------------------

class TestGenerateTemplateOverride:
    def test_valid_template_accepted(self):
        r = _post({"text": _MEETING_TEXT, "template_id": "ops_review_v1"})
        assert r.status_code == 200
        assert r.json()["template_id"] == "ops_review_v1"

    def test_architecture_template_accepted(self):
        r = _post({"text": _MEETING_TEXT, "template_id": "architecture_overview_v1"})
        assert r.status_code == 200
        assert r.json()["template_id"] == "architecture_overview_v1"

    def test_invalid_template_returns_4xx(self):
        r = _post({"text": _MEETING_TEXT, "template_id": "nonexistent_v99"})
        assert r.status_code >= 400

    def test_invalid_template_error_body(self):
        r = _post({"text": _MEETING_TEXT, "template_id": "nonexistent_v99"})
        body = r.json()
        # FastAPI wraps HTTPException as {"detail": "..."}
        assert "detail" in body or "error" in body


# ---------------------------------------------------------------------------
# Invalid mode
# ---------------------------------------------------------------------------

class TestGenerateInvalidMode:
    def test_invalid_mode_returns_400(self):
        r = _post({"text": _MEETING_TEXT, "mode": "bad-mode"})
        assert r.status_code == 400

    def test_invalid_mode_error_in_body(self):
        r = _post({"text": _MEETING_TEXT, "mode": "bad-mode"})
        body = r.json()
        assert "detail" in body or "error" in body

    def test_invalid_mode_message_mentions_mode(self):
        r = _post({"text": _MEETING_TEXT, "mode": "llm"})
        body_str = str(r.json()).lower()
        assert "mode" in body_str or "deterministic" in body_str

    def test_invalid_mode_error_has_request_id(self):
        r = _post({"text": _MEETING_TEXT, "mode": "bad-mode"})
        detail = r.json()["detail"]
        assert "request_id" in detail
        uuid.UUID(detail["request_id"])  # must be valid UUID


# ---------------------------------------------------------------------------
# Artifacts via API
# ---------------------------------------------------------------------------

class TestGenerateArtifacts:
    def test_artifacts_returns_artifact_paths(self):
        r = _post({"text": _MEETING_TEXT, "artifacts": True})
        assert r.status_code == 200
        assert r.json()["artifact_paths"] is not None

    def test_artifact_paths_has_spec_key(self):
        r = _post({"text": _MEETING_TEXT, "artifacts": True})
        assert "spec" in r.json()["artifact_paths"]

    def test_artifact_spec_json_exists(self):
        r = _post({"text": _MEETING_TEXT, "artifacts": True})
        spec_path = Path(r.json()["artifact_paths"]["spec"])
        assert spec_path.exists()

    def test_no_artifact_paths_when_disabled(self):
        r = _post({"text": _MEETING_TEXT, "artifacts": False})
        assert r.json()["artifact_paths"] is None

    def test_artifacts_preview_only_no_artifacts(self):
        """preview_only skips render and artifacts (no output path = no artifacts dir)."""
        r = _post({"text": _MEETING_TEXT, "artifacts": True, "preview_only": True})
        assert r.status_code == 200
        # artifact_paths is None because output_path is None in preview mode
        assert r.json()["artifact_paths"] is None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestGenerateEdgeCases:
    def test_empty_text_returns_200(self):
        r = _post({"text": ""})
        assert r.status_code == 200

    def test_missing_text_returns_422(self):
        r = _post({})
        assert r.status_code == 422

    def test_response_is_deterministic(self):
        r1 = _post({"text": _ADO_TEXT, "preview_only": True})
        r2 = _post({"text": _ADO_TEXT, "preview_only": True})
        assert r1.json()["playbook_id"] == r2.json()["playbook_id"]
        assert r1.json()["slide_count"] == r2.json()["slide_count"]

    def test_notes_field_present(self):
        r = _post({"text": _MEETING_TEXT})
        body = r.json()
        assert "notes" in body  # may be None or a string


# ---------------------------------------------------------------------------
# request_id in responses
# ---------------------------------------------------------------------------

class TestRequestId:
    def test_request_id_present(self):
        r = _post({"text": _MEETING_TEXT})
        assert "request_id" in r.json()

    def test_request_id_is_valid_uuid(self):
        r = _post({"text": _MEETING_TEXT})
        uuid.UUID(r.json()["request_id"])  # raises if invalid

    def test_request_id_differs_between_requests(self):
        r1 = _post({"text": _MEETING_TEXT, "preview_only": True})
        r2 = _post({"text": _MEETING_TEXT, "preview_only": True})
        assert r1.json()["request_id"] != r2.json()["request_id"]

    def test_request_id_present_in_preview_mode(self):
        r = _post({"text": _MEETING_TEXT, "preview_only": True})
        assert "request_id" in r.json()
        uuid.UUID(r.json()["request_id"])
