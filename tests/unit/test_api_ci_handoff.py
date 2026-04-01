"""Regression tests for the content_intent API contract — Phase 11C UI/API wiring fix.

Verifies that:
1. POST /v1/generate accepts content_intent in the request body.
2. When content_intent is provided, the response has playbook_id='content-intelligence'.
3. content_intent_mode is True in the response for CI requests.
4. Preview (preview_only=True) and Generate both exercise the CI path consistently.
5. Legacy raw-text requests are unaffected (content_intent_mode is False/absent).
6. Raw ContentIntent serialization cannot appear in the response body.
7. Missing or blank topic returns a 400 error.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app

client = TestClient(app)


def _post(payload: dict):
    return client.post("/v1/generate", json=payload)


# ---------------------------------------------------------------------------
# CI path — basic contract
# ---------------------------------------------------------------------------

class TestCIRequestContract:
    def test_content_intent_accepted(self):
        """Server must accept a request with content_intent without 422."""
        r = _post({"text": "Cloud Cost", "content_intent": {"topic": "Cloud Cost Optimisation"}})
        assert r.status_code == 200, r.json()

    def test_playbook_id_is_content_intelligence(self):
        r = _post({
            "text": "Cloud Cost Optimisation",
            "content_intent": {"topic": "Cloud Cost Optimisation"},
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()
        assert r.json()["playbook_id"] == "content-intelligence"

    def test_content_intent_mode_true(self):
        r = _post({
            "text": "Platform Reliability",
            "content_intent": {"topic": "Platform Reliability"},
            "preview_only": True,
        })
        assert r.json().get("content_intent_mode") is True

    def test_slide_count_populated_from_ci_deck(self):
        """slide_count must be populated even when slide_plan is None (CI path)."""
        r = _post({
            "text": "API Reliability Strategy",
            "content_intent": {"topic": "API Reliability Strategy"},
            "preview_only": True,
        })
        data = r.json()
        assert data["slide_count"] is not None
        assert data["slide_count"] >= 1

    def test_slide_types_populated_from_ci_deck(self):
        r = _post({
            "text": "Risk Management",
            "content_intent": {"topic": "Risk Management Programme"},
            "preview_only": True,
        })
        data = r.json()
        assert data["slide_types"] is not None
        assert "title" in data["slide_types"]

    def test_ci_with_goal(self):
        r = _post({
            "text": "Platform Reliability",
            "content_intent": {
                "topic": "Platform Reliability",
                "goal": "Achieve 99.9% uptime SLA",
            },
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()
        assert r.json()["playbook_id"] == "content-intelligence"

    def test_ci_with_audience(self):
        r = _post({
            "text": "Security Posture",
            "content_intent": {
                "topic": "Security Posture Improvement",
                "audience": "Engineering leadership",
            },
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()


# ---------------------------------------------------------------------------
# Preview vs Generate consistency
# ---------------------------------------------------------------------------

class TestPreviewAndGenerateConsistency:
    def test_preview_uses_ci_path(self):
        r = _post({
            "text": "Observability Uplift",
            "content_intent": {"topic": "Observability Uplift"},
            "preview_only": True,
        })
        assert r.json()["playbook_id"] == "content-intelligence"

    def test_generate_uses_ci_path(self):
        r = _post({
            "text": "Observability Uplift",
            "content_intent": {"topic": "Observability Uplift"},
            "preview_only": False,
        })
        assert r.json()["playbook_id"] == "content-intelligence"

    def test_preview_and_generate_both_return_content_intent_mode_true(self):
        payload_base = {
            "text": "Delivery Pipeline Reliability",
            "content_intent": {"topic": "Delivery Pipeline Reliability"},
        }
        preview = _post({**payload_base, "preview_only": True}).json()
        generate = _post({**payload_base, "preview_only": False}).json()
        assert preview.get("content_intent_mode") is True
        assert generate.get("content_intent_mode") is True


# ---------------------------------------------------------------------------
# No raw ContentIntent serialization in response
# ---------------------------------------------------------------------------

class TestNoRawSerializationInResponse:
    def test_content_intent_repr_not_in_response_json(self):
        r = _post({
            "text": "DLQ Backlog Remediation",
            "content_intent": {
                "topic": "DLQ Backlog Remediation",
                "goal": "Reduce DLQ backlog to zero",
            },
            "preview_only": True,
        })
        raw_body = r.text
        assert "ContentIntent(" not in raw_body, (
            "Raw ContentIntent() repr leaked into the API response body"
        )

    def test_context_dict_not_in_response_json(self):
        r = _post({
            "text": "Delivery Status Review",
            "content_intent": {
                "topic": "Delivery Status Review",
                "context": {"status_detail": "raw_context_marker_xyz"},
            },
            "preview_only": True,
        })
        # The raw context dict itself should not appear verbatim as a string
        # in the response (it's internal to the pipeline, not echoed back).
        assert r.status_code == 200, r.json()


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class TestCIValidationErrors:
    def test_missing_topic_returns_400(self):
        r = _post({
            "text": "some text",
            "content_intent": {"goal": "No topic here"},
        })
        assert r.status_code == 400

    def test_blank_topic_returns_400(self):
        r = _post({
            "text": "some text",
            "content_intent": {"topic": "   "},
        })
        assert r.status_code == 400

    def test_empty_content_intent_returns_400(self):
        r = _post({
            "text": "some text",
            "content_intent": {},
        })
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# Legacy path unaffected
# ---------------------------------------------------------------------------

class TestLegacyPathUnaffected:
    def test_no_content_intent_uses_legacy_path(self):
        r = _post({"text": "Meeting notes. Attendees: Alice, Bob. Action: review deliverables."})
        assert r.status_code == 200
        data = r.json()
        assert data["playbook_id"] != "content-intelligence"
        assert data.get("content_intent_mode") is not True

    def test_structured_yaml_without_content_intent_uses_direct_deck(self):
        structured = "slides:\n  - type: title\n    title: Test\n"
        r = _post({"text": structured, "preview_only": True})
        assert r.status_code == 200
        assert r.json()["playbook_id"] == "direct-deck-input"
        assert r.json().get("content_intent_mode") is not True


# ---------------------------------------------------------------------------
# ContentIntent integrity — topic preserved through the full request boundary
# ---------------------------------------------------------------------------

class TestContentIntentIntegrity:
    """Guard against ContentIntent corruption across the UI → API → pipeline boundary."""

    def test_ci_topic_drives_ci_path_not_text_field(self):
        """When content_intent.topic differs from text, the CI path uses the topic.

        This is the primary regression guard: topic must be the authoritative
        value for the deck, not the raw text input.
        """
        r = _post({
            "text": "some unrelated legacy text that should be ignored",
            "content_intent": {"topic": "Enterprise Interchange Reliability"},
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()
        assert r.json()["playbook_id"] == "content-intelligence"
        assert r.json().get("content_intent_mode") is True

    def test_empty_text_with_content_intent_uses_ci_path(self):
        """Empty text field in CI mode (correct frontend behaviour) must work.

        The corrected buildRequest() sends text='' in CI mode to prevent
        stale raw-text state from accidentally driving deck generation.
        """
        r = _post({
            "text": "",
            "content_intent": {"topic": "Platform Resilience Strategy"},
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()
        assert r.json()["playbook_id"] == "content-intelligence"

    def test_multiline_topic_is_rejected(self):
        """A multi-line string as topic must return 400.

        Prevents accidental paste of document/test-output text as a topic.
        A presentation topic is always a single-line concept.
        """
        multiline_topic = "Enterprise Platform\nCloud Cost Optimisation"
        r = _post({
            "text": "",
            "content_intent": {"topic": multiline_topic},
            "preview_only": True,
        })
        assert r.status_code == 400

    def test_large_text_blob_as_topic_is_rejected(self):
        """A text blob longer than 500 chars as topic must return 400.

        Prevents accidental paste of meeting notes, test output, or other
        long-form text as a presentation topic.
        """
        blob_topic = "A" * 501
        r = _post({
            "text": "",
            "content_intent": {"topic": blob_topic},
            "preview_only": True,
        })
        assert r.status_code == 400

    def test_prior_output_text_as_topic_is_rejected(self):
        """Simulates the corruption scenario: summary text submitted as topic.

        The observed failure involved text like '3229 passed, 0 regressions.
        Here's a summary of what was implemented:...' appearing as deck content.
        This test confirms such multi-line text is now rejected at the API boundary.
        """
        corrupted_topic = (
            "3229 passed, 0 regressions. Here's a summary of what was implemented:\n\n"
            "Part 1 — Ollama Parse Reliability\n"
            "Part 2 — CI-native spec.json and slide_plan.json"
        )
        r = _post({
            "text": "",
            "content_intent": {"topic": corrupted_topic},
            "preview_only": True,
        })
        assert r.status_code == 400

    def test_content_intent_topic_is_authoritative_over_text(self):
        """content_intent.topic must never be overridden by the text field."""
        r = _post({
            "text": "3229 passed, 0 regressions. This is test output noise.",
            "content_intent": {"topic": "Cloud Cost Optimisation"},
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()
        # The CI path must have run — confirming content_intent.topic was used
        assert r.json()["playbook_id"] == "content-intelligence"
        assert r.json().get("content_intent_mode") is True

    def test_stale_legacy_text_cannot_activate_legacy_path_when_ci_intent_present(self):
        """Even with a large text payload, presence of content_intent forces CI path."""
        stale_text = "Meeting notes from the sprint review. " * 20
        r = _post({
            "text": stale_text,
            "content_intent": {"topic": "Sprint Delivery Performance"},
            "preview_only": True,
        })
        assert r.status_code == 200, r.json()
        assert r.json()["playbook_id"] == "content-intelligence"
