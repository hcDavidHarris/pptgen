"""Tests for template resolution logic — Phase 8 Stage 1."""
from __future__ import annotations

import logging
from typing import Optional

import pytest

from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry
from pptgen.templates.resolution import (
    resolve_template_default_version,
    resolve_template_for_replay,
    resolve_template_for_run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(template_id: str, version: str) -> TemplateVersion:
    return TemplateVersion(
        version_id=f"vid-{template_id}-{version}",
        template_id=template_id,
        version=version,
        template_revision_hash="ab12cd34ef56ab12",
    )


def _make_template(
    template_id: str,
    lifecycle_status: str = "approved",
    versions: list[str] | None = None,
) -> Template:
    vers = [_make_version(template_id, v) for v in (versions or ["1.0.0"])]
    return Template(
        template_id=template_id,
        template_key=template_id,
        name=template_id.title(),
        lifecycle_status=lifecycle_status,
        versions=vers,
    )


def _registry(*templates: Template) -> VersionedTemplateRegistry:
    return VersionedTemplateRegistry(list(templates))


# ---------------------------------------------------------------------------
# resolve_template_default_version
# ---------------------------------------------------------------------------

def test_default_version_returns_latest():
    tmpl = _make_template("tmpl_a", versions=["1.0.0", "2.0.0", "1.5.0"])
    reg = _registry(tmpl)
    v = resolve_template_default_version(reg, "tmpl_a")
    assert v is not None
    assert v.version == "2.0.0"


def test_default_version_returns_none_for_unknown_template():
    reg = _registry()
    assert resolve_template_default_version(reg, "nonexistent") is None


def test_default_version_returns_none_for_deprecated():
    tmpl = _make_template("tmpl_a", lifecycle_status="deprecated")
    reg = _registry(tmpl)
    assert resolve_template_default_version(reg, "tmpl_a") is None


def test_default_version_returns_none_for_draft():
    tmpl = _make_template("tmpl_a", lifecycle_status="draft")
    reg = _registry(tmpl)
    assert resolve_template_default_version(reg, "tmpl_a") is None


def test_default_version_allows_review():
    tmpl = _make_template("tmpl_a", lifecycle_status="review")
    reg = _registry(tmpl)
    v = resolve_template_default_version(reg, "tmpl_a")
    assert v is not None


# ---------------------------------------------------------------------------
# resolve_template_for_run
# ---------------------------------------------------------------------------

def test_for_run_no_version_uses_default():
    tmpl = _make_template("tmpl_a", versions=["1.0.0", "2.0.0"])
    reg = _registry(tmpl)
    v = resolve_template_for_run(reg, "tmpl_a")
    assert v is not None
    assert v.version == "2.0.0"


def test_for_run_pinned_version_returns_exact():
    tmpl = _make_template("tmpl_a", versions=["1.0.0", "2.0.0"])
    reg = _registry(tmpl)
    v = resolve_template_for_run(reg, "tmpl_a", version="1.0.0")
    assert v is not None
    assert v.version == "1.0.0"


def test_for_run_pinned_version_not_found_returns_none():
    tmpl = _make_template("tmpl_a", versions=["1.0.0"])
    reg = _registry(tmpl)
    v = resolve_template_for_run(reg, "tmpl_a", version="9.9.9")
    assert v is None


def test_for_run_unknown_template_returns_none():
    reg = _registry()
    assert resolve_template_for_run(reg, "nonexistent") is None


def test_for_run_emits_log_event(caplog):
    tmpl = _make_template("tmpl_a")
    reg = _registry(tmpl)
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_run(reg, "tmpl_a", run_id="run-001")
    assert any("template_resolved" in r.message for r in caplog.records)


def test_for_run_no_log_when_not_found(caplog):
    reg = _registry()
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_run(reg, "nonexistent")
    assert not any("template_resolved" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# resolve_template_for_replay
# ---------------------------------------------------------------------------

def test_for_replay_returns_pinned_version():
    tmpl = _make_template("tmpl_a", versions=["1.0.0", "2.0.0"])
    reg = _registry(tmpl)
    v = resolve_template_for_replay(reg, "tmpl_a", pinned_version="1.0.0")
    assert v is not None
    assert v.version == "1.0.0"


def test_for_replay_does_not_use_default():
    """Even if 2.0.0 is the latest approved, replay pins exactly to 2.0.0 by string match."""
    tmpl = _make_template("tmpl_a", versions=["1.0.0", "2.0.0"])
    reg = _registry(tmpl)
    v = resolve_template_for_replay(reg, "tmpl_a", pinned_version="2.0.0")
    assert v is not None
    assert v.version == "2.0.0"


def test_for_replay_missing_version_returns_none():
    tmpl = _make_template("tmpl_a", versions=["1.0.0"])
    reg = _registry(tmpl)
    assert resolve_template_for_replay(reg, "tmpl_a", pinned_version="0.0.1") is None


def test_for_replay_emits_log_event(caplog):
    tmpl = _make_template("tmpl_a")
    reg = _registry(tmpl)
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_replay(reg, "tmpl_a", "1.0.0", run_id="run-replay")
    assert any("template_resolved" in r.message for r in caplog.records)


def test_for_replay_no_log_when_not_found(caplog):
    reg = _registry()
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_replay(reg, "tmpl_a", "1.0.0")
    assert not any("template_resolved" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Log event content
# ---------------------------------------------------------------------------

def test_log_event_contains_resolution_mode(caplog):
    tmpl = _make_template("tmpl_a")
    reg = _registry(tmpl)
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_run(reg, "tmpl_a", version="1.0.0")
    record = next(r for r in caplog.records if "template_resolved" in r.message)
    assert getattr(record, "resolution_mode", None) == "new_run_pinned"


def test_log_event_default_mode(caplog):
    tmpl = _make_template("tmpl_a")
    reg = _registry(tmpl)
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_run(reg, "tmpl_a")
    record = next(r for r in caplog.records if "template_resolved" in r.message)
    assert getattr(record, "resolution_mode", None) == "new_run_default"


def test_log_event_replay_mode(caplog):
    tmpl = _make_template("tmpl_a")
    reg = _registry(tmpl)
    with caplog.at_level(logging.INFO, logger="pptgen.templates.resolution"):
        resolve_template_for_replay(reg, "tmpl_a", "1.0.0")
    record = next(r for r in caplog.records if "template_resolved" in r.message)
    assert getattr(record, "resolution_mode", None) == "replay"
