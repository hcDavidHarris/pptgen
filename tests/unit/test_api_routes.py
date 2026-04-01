"""Tests for metadata API routes: /v1/health, /v1/templates, /v1/playbooks."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from pptgen.api.server import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_returns_200(self):
        r = client.get("/v1/health")
        assert r.status_code == 200

    def test_returns_ok_status(self):
        r = client.get("/v1/health")
        assert r.json()["status"] == "ok"

    def test_content_type_is_json(self):
        r = client.get("/v1/health")
        assert "application/json" in r.headers["content-type"]

    def test_deterministic(self):
        r1 = client.get("/v1/health")
        r2 = client.get("/v1/health")
        assert r1.json()["status"] == r2.json()["status"]

    def test_request_id_present(self):
        r = client.get("/v1/health")
        assert "request_id" in r.json()

    def test_request_id_is_valid_uuid(self):
        r = client.get("/v1/health")
        uuid.UUID(r.json()["request_id"])  # raises if invalid

    def test_request_id_differs_between_requests(self):
        r1 = client.get("/v1/health")
        r2 = client.get("/v1/health")
        assert r1.json()["request_id"] != r2.json()["request_id"]


class TestTemplatesEndpoint:
    def test_returns_200(self):
        r = client.get("/v1/templates")
        assert r.status_code == 200

    def test_response_has_templates_key(self):
        r = client.get("/v1/templates")
        assert "templates" in r.json()

    def test_templates_is_list(self):
        r = client.get("/v1/templates")
        assert isinstance(r.json()["templates"], list)

    def test_templates_non_empty(self):
        r = client.get("/v1/templates")
        assert len(r.json()["templates"]) > 0

    def test_ops_review_present(self):
        r = client.get("/v1/templates")
        assert "ops_review_v1" in r.json()["templates"]

    def test_architecture_overview_present(self):
        r = client.get("/v1/templates")
        assert "architecture_overview_v1" in r.json()["templates"]

    def test_executive_brief_present(self):
        r = client.get("/v1/templates")
        assert "executive_brief_v1" in r.json()["templates"]

    def test_sorted_alphabetically(self):
        r = client.get("/v1/templates")
        templates = r.json()["templates"]
        assert templates == sorted(templates)

    def test_deterministic(self):
        r1 = client.get("/v1/templates")
        r2 = client.get("/v1/templates")
        assert r1.json()["templates"] == r2.json()["templates"]

    def test_request_id_present(self):
        r = client.get("/v1/templates")
        assert "request_id" in r.json()

    def test_request_id_is_valid_uuid(self):
        r = client.get("/v1/templates")
        uuid.UUID(r.json()["request_id"])

    def test_request_id_differs_between_requests(self):
        r1 = client.get("/v1/templates")
        r2 = client.get("/v1/templates")
        assert r1.json()["request_id"] != r2.json()["request_id"]


class TestPlaybooksEndpoint:
    def test_returns_200(self):
        r = client.get("/v1/playbooks")
        assert r.status_code == 200

    def test_response_has_playbooks_key(self):
        r = client.get("/v1/playbooks")
        assert "playbooks" in r.json()

    def test_playbooks_is_list(self):
        r = client.get("/v1/playbooks")
        assert isinstance(r.json()["playbooks"], list)

    def test_playbooks_non_empty(self):
        r = client.get("/v1/playbooks")
        assert len(r.json()["playbooks"]) > 0

    def test_meeting_notes_playbook_present(self):
        r = client.get("/v1/playbooks")
        assert "meeting-notes-to-eos-rocks" in r.json()["playbooks"]

    def test_ado_playbook_present(self):
        r = client.get("/v1/playbooks")
        assert "ado-summary-to-weekly-delivery" in r.json()["playbooks"]

    def test_architecture_playbook_present(self):
        r = client.get("/v1/playbooks")
        assert "architecture-notes-to-adr-deck" in r.json()["playbooks"]

    def test_devops_playbook_present(self):
        r = client.get("/v1/playbooks")
        assert "devops-metrics-to-scorecard" in r.json()["playbooks"]

    def test_sorted_alphabetically(self):
        r = client.get("/v1/playbooks")
        playbooks = r.json()["playbooks"]
        assert playbooks == sorted(playbooks)

    def test_request_id_present(self):
        r = client.get("/v1/playbooks")
        assert "request_id" in r.json()

    def test_request_id_is_valid_uuid(self):
        r = client.get("/v1/playbooks")
        uuid.UUID(r.json()["request_id"])

    def test_request_id_differs_between_requests(self):
        r1 = client.get("/v1/playbooks")
        r2 = client.get("/v1/playbooks")
        assert r1.json()["request_id"] != r2.json()["request_id"]
