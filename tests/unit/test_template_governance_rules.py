"""Tests for governance rule helpers — Phase 8 Stage 3.

Covers:
- is_new_run_allowed / is_replay_allowed for all lifecycle states
- validate_lifecycle_transition (valid / invalid proposed states)
- validate_version_promotable (version exists, not deprecated)
- validate_version_deprecatable (version exists, not already deprecated, not sole version)
- get_effective_lifecycle (manifest vs governance override)
- get_effective_default_version (governance pin → semver fallback, deprecated skipped)
- apply_governance_to_version
- GovernanceStore: set/get default version, deprecate/undeprecate, lifecycle overrides, audit trail
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pptgen.templates.governance import (
    GovernanceStore,
    apply_governance_to_version,
    get_effective_default_version,
    get_effective_lifecycle,
    is_new_run_allowed,
    is_replay_allowed,
    validate_lifecycle_transition,
    validate_version_deprecatable,
    validate_version_promotable,
)
from pptgen.templates.models import Template, TemplateVersion
from pptgen.templates.registry import VersionedTemplateRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_version(template_id: str, version: str) -> TemplateVersion:
    return TemplateVersion(
        version_id=f"vid-{template_id}-{version}",
        template_id=template_id,
        version=version,
        template_revision_hash="abc123def456ab12",
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
        name=template_id.replace("_", " ").title(),
        lifecycle_status=lifecycle_status,
        versions=vers,
    )


def _registry(*templates: Template) -> VersionedTemplateRegistry:
    return VersionedTemplateRegistry(list(templates))


@pytest.fixture
def gov(tmp_path):
    store = GovernanceStore(tmp_path / "gov.db")
    yield store
    store.close()


@pytest.fixture
def reg():
    return _registry(
        _make_template("tmpl_a", lifecycle_status="approved", versions=["1.0.0", "1.1.0", "2.0.0"]),
        _make_template("tmpl_b", lifecycle_status="draft", versions=["0.1.0"]),
        _make_template("tmpl_deprecated", lifecycle_status="deprecated", versions=["1.0.0"]),
    )


# ---------------------------------------------------------------------------
# is_new_run_allowed
# ---------------------------------------------------------------------------

def test_new_run_allowed_approved():
    assert is_new_run_allowed("approved") is True


def test_new_run_blocked_draft():
    assert is_new_run_allowed("draft") is False


def test_new_run_blocked_review():
    assert is_new_run_allowed("review") is False


def test_new_run_blocked_deprecated():
    assert is_new_run_allowed("deprecated") is False


def test_new_run_blocked_unknown():
    assert is_new_run_allowed("unknown_state") is False


# ---------------------------------------------------------------------------
# is_replay_allowed
# ---------------------------------------------------------------------------

def test_replay_allowed_for_all_known_states():
    for state in ("draft", "review", "approved", "deprecated"):
        assert is_replay_allowed(state) is True


def test_replay_allowed_unknown_defaults_true():
    assert is_replay_allowed("totally_unknown") is True


# ---------------------------------------------------------------------------
# validate_lifecycle_transition
# ---------------------------------------------------------------------------

def test_transition_approved_to_deprecated_ok():
    validate_lifecycle_transition("approved", "deprecated")  # should not raise


def test_transition_draft_to_review_ok():
    validate_lifecycle_transition("draft", "review")


def test_transition_any_to_approved_ok():
    for state in ("draft", "review", "deprecated"):
        validate_lifecycle_transition(state, "approved")


def test_transition_invalid_proposed_raises():
    with pytest.raises(ValueError, match="Invalid lifecycle_status"):
        validate_lifecycle_transition("approved", "nonexistent_state")


def test_transition_empty_string_raises():
    with pytest.raises(ValueError):
        validate_lifecycle_transition("approved", "")


# ---------------------------------------------------------------------------
# validate_version_promotable
# ---------------------------------------------------------------------------

def test_promotable_ok(reg, gov):
    validate_version_promotable(reg, gov, "tmpl_a", "1.0.0")  # should not raise


def test_promotable_unknown_template_raises(reg, gov):
    with pytest.raises(ValueError, match="Template not found"):
        validate_version_promotable(reg, gov, "nonexistent", "1.0.0")


def test_promotable_unknown_version_raises(reg, gov):
    with pytest.raises(ValueError, match="Version not found"):
        validate_version_promotable(reg, gov, "tmpl_a", "9.9.9")


def test_promotable_deprecated_version_raises(reg, gov):
    gov.deprecate_version("tmpl_a", "1.0.0", reason="old")
    with pytest.raises(ValueError, match="Cannot promote deprecated"):
        validate_version_promotable(reg, gov, "tmpl_a", "1.0.0")


# ---------------------------------------------------------------------------
# validate_version_deprecatable
# ---------------------------------------------------------------------------

def test_deprecatable_ok(reg, gov):
    validate_version_deprecatable(reg, gov, "tmpl_a", "1.0.0")  # should not raise


def test_deprecatable_unknown_template_raises(reg, gov):
    with pytest.raises(ValueError, match="Template not found"):
        validate_version_deprecatable(reg, gov, "nonexistent", "1.0.0")


def test_deprecatable_unknown_version_raises(reg, gov):
    with pytest.raises(ValueError, match="Version not found"):
        validate_version_deprecatable(reg, gov, "tmpl_a", "9.9.9")


def test_deprecatable_already_deprecated_raises(reg, gov):
    gov.deprecate_version("tmpl_a", "1.0.0", reason="old")
    with pytest.raises(ValueError, match="already deprecated"):
        validate_version_deprecatable(reg, gov, "tmpl_a", "1.0.0")


def test_deprecatable_sole_version_raises():
    """Cannot deprecate the only non-deprecated version of a template."""
    reg = _registry(_make_template("solo", versions=["1.0.0"]))
    gov_path = Path("/tmp/gov_sole_test.db")
    gov = GovernanceStore(gov_path)
    try:
        with pytest.raises(ValueError, match="only non-deprecated"):
            validate_version_deprecatable(reg, gov, "solo", "1.0.0")
    finally:
        gov.close()
        gov_path.unlink(missing_ok=True)


def test_deprecatable_sole_remaining_after_others_deprecated(reg, gov):
    """Can deprecate 1.0.0 and 1.1.0, but not 2.0.0 (sole remaining)."""
    gov.deprecate_version("tmpl_a", "1.0.0", reason="old")
    gov.deprecate_version("tmpl_a", "1.1.0", reason="old")
    with pytest.raises(ValueError, match="only non-deprecated"):
        validate_version_deprecatable(reg, gov, "tmpl_a", "2.0.0")


# ---------------------------------------------------------------------------
# get_effective_lifecycle
# ---------------------------------------------------------------------------

def test_effective_lifecycle_manifest_fallback(reg, gov):
    assert get_effective_lifecycle(reg, gov, "tmpl_a") == "approved"


def test_effective_lifecycle_manifest_draft(reg, gov):
    assert get_effective_lifecycle(reg, gov, "tmpl_b") == "draft"


def test_effective_lifecycle_governance_override(reg, gov):
    gov.set_lifecycle("tmpl_a", "deprecated")
    assert get_effective_lifecycle(reg, gov, "tmpl_a") == "deprecated"


def test_effective_lifecycle_override_then_clear(reg, gov):
    gov.set_lifecycle("tmpl_a", "draft")
    assert get_effective_lifecycle(reg, gov, "tmpl_a") == "draft"
    # Override to approved to simulate "undo"
    gov.set_lifecycle("tmpl_a", "approved")
    assert get_effective_lifecycle(reg, gov, "tmpl_a") == "approved"


def test_effective_lifecycle_missing_template_returns_draft(reg, gov):
    assert get_effective_lifecycle(reg, gov, "no_such_template") == "draft"


# ---------------------------------------------------------------------------
# get_effective_default_version
# ---------------------------------------------------------------------------

def test_effective_default_version_governance_pin(reg, gov):
    gov.set_default_version("tmpl_a", "1.0.0")
    result = get_effective_default_version(reg, gov, "tmpl_a")
    assert result is not None
    assert result.version == "1.0.0"


def test_effective_default_version_semver_fallback_no_pin(reg, gov):
    """Without a governance pin, the highest semver non-deprecated version is returned."""
    result = get_effective_default_version(reg, gov, "tmpl_a")
    assert result is not None
    assert result.version == "2.0.0"


def test_effective_default_version_deprecated_pin_falls_back(reg, gov):
    """When the pinned version is deprecated, fall back to semver."""
    gov.set_default_version("tmpl_a", "1.0.0")
    gov.deprecate_version("tmpl_a", "1.0.0", reason="old")
    result = get_effective_default_version(reg, gov, "tmpl_a")
    assert result is not None
    assert result.version == "2.0.0"


def test_effective_default_version_skips_deprecated_in_semver_fallback(reg, gov):
    """Semver fallback must skip deprecated versions."""
    gov.deprecate_version("tmpl_a", "2.0.0", reason="bad release")
    result = get_effective_default_version(reg, gov, "tmpl_a")
    assert result is not None
    assert result.version == "1.1.0"


def test_effective_default_version_none_when_not_approved(reg, gov):
    """Draft templates should not resolve a default version."""
    result = get_effective_default_version(reg, gov, "tmpl_b")
    assert result is None


def test_effective_default_version_none_when_lifecycle_overridden_to_deprecated(reg, gov):
    gov.set_lifecycle("tmpl_a", "deprecated")
    result = get_effective_default_version(reg, gov, "tmpl_a")
    assert result is None


# ---------------------------------------------------------------------------
# apply_governance_to_version
# ---------------------------------------------------------------------------

def test_apply_governance_sets_is_default(reg, gov):
    ver = reg.get_template_version("tmpl_a", "2.0.0")
    gov.set_default_version("tmpl_a", "2.0.0")
    result = apply_governance_to_version(ver, gov, "2.0.0")
    assert result.is_default is True
    assert result.deprecated_at is None


def test_apply_governance_not_default_for_non_pinned(reg, gov):
    ver = reg.get_template_version("tmpl_a", "1.0.0")
    gov.set_default_version("tmpl_a", "2.0.0")
    result = apply_governance_to_version(ver, gov, "2.0.0")
    assert result.is_default is False


def test_apply_governance_sets_deprecated_fields(reg, gov):
    gov.deprecate_version("tmpl_a", "1.0.0", reason="too old")
    ver = reg.get_template_version("tmpl_a", "1.0.0")
    result = apply_governance_to_version(ver, gov, None)
    assert result.deprecated_at is not None
    assert result.deprecation_reason == "too old"


def test_apply_governance_sets_promotion_timestamp(reg, gov):
    gov.set_default_version("tmpl_a", "2.0.0")
    ver = reg.get_template_version("tmpl_a", "2.0.0")
    result = apply_governance_to_version(ver, gov, "2.0.0")
    assert result.promotion_timestamp is not None


# ---------------------------------------------------------------------------
# GovernanceStore — audit trail
# ---------------------------------------------------------------------------

def test_audit_event_appended(gov):
    gov.add_audit_event(
        "template_version_promoted",
        template_id="tmpl_a",
        template_version="2.0.0",
        actor="alice",
        reason="releasing v2",
    )
    events = gov.list_audit_events(template_id="tmpl_a")
    assert len(events) == 1
    evt = events[0]
    assert evt["event_type"] == "template_version_promoted"
    assert evt["template_id"] == "tmpl_a"
    assert evt["template_version"] == "2.0.0"
    assert evt["actor"] == "alice"
    assert evt["reason"] == "releasing v2"
    assert evt["timestamp"]


def test_audit_events_newest_first(gov):
    for i in range(3):
        gov.add_audit_event("evt", template_id="tmpl_a", template_version=str(i))
    events = gov.list_audit_events(template_id="tmpl_a")
    assert events[0]["template_version"] == "2"
    assert events[-1]["template_version"] == "0"


def test_audit_events_filtered_by_template(gov):
    gov.add_audit_event("evt", template_id="tmpl_a")
    gov.add_audit_event("evt", template_id="tmpl_b")
    events_a = gov.list_audit_events(template_id="tmpl_a")
    assert all(e["template_id"] == "tmpl_a" for e in events_a)


def test_audit_events_limit(gov):
    for i in range(10):
        gov.add_audit_event("evt", template_id="tmpl_a")
    events = gov.list_audit_events(template_id="tmpl_a", limit=5)
    assert len(events) == 5


def test_audit_metadata_round_trips(gov):
    gov.add_audit_event(
        "evt",
        template_id="tmpl_a",
        previous_default="1.0.0",
        extra_field="value",
    )
    events = gov.list_audit_events(template_id="tmpl_a")
    assert events[0]["metadata"] is not None
    assert events[0]["metadata"]["previous_default"] == "1.0.0"
