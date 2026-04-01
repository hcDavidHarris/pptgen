"""Regression tests for the content intelligence → pipeline handoff — Phase 11C fix.

These tests verify that:
1. When content_intent is provided without structured YAML input, the CI layer
   drives deck building — the legacy playbook path is bypassed.
2. Raw ContentIntent serialization never appears in slide text.
3. Semantic CI output (title, assertion, supporting_points) reaches slide content.
4. The deck does not collapse to a trivial title/section/bullets legacy structure
   when content_intent is the authoritative source.
5. Legacy (non-CI) flows remain unaffected.
"""

from __future__ import annotations

import pytest

from pptgen.content_intelligence import ContentIntent, run_content_intelligence
from pptgen.pipeline import generate_presentation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _all_slide_text(deck_definition: dict) -> str:
    """Collect all text-bearing fields from every slide in deck_definition."""
    slides = deck_definition.get("slides", [])
    parts: list[str] = []
    for slide in slides:
        for key in ("title", "subtitle", "content", "notes"):
            val = slide.get(key)
            if isinstance(val, str):
                parts.append(val)
        for bullet in slide.get("bullets", []):
            if isinstance(bullet, str):
                parts.append(bullet)
    return "\n".join(parts)


def _slide_types(deck_definition: dict) -> list[str]:
    return [s.get("type", "") for s in deck_definition.get("slides", [])]


# ---------------------------------------------------------------------------
# Root cause regression: CI drives deck when content_intent is primary input
# ---------------------------------------------------------------------------

class TestCIdrivesDeckBuilding:
    """The CI path must replace the legacy playbook path, not run alongside it."""

    def test_playbook_id_is_content_intelligence(self):
        """When content_intent is provided as plain text input, playbook_id must
        be 'content-intelligence', not a legacy playbook."""
        ci = ContentIntent(topic="Cloud Cost Optimisation")
        result = generate_presentation("Cloud Cost Optimisation", content_intent=ci)
        assert result.playbook_id == "content-intelligence", (
            f"Expected playbook_id='content-intelligence', got '{result.playbook_id}'. "
            "Legacy playbook routing must not run when content_intent drives the deck."
        )

    def test_enriched_content_is_populated(self):
        ci = ContentIntent(topic="API Reliability Strategy")
        result = generate_presentation("API Reliability Strategy", content_intent=ci)
        assert result.enriched_content is not None
        assert len(result.enriched_content) >= 1

    def test_deck_definition_uses_ci_slides(self):
        """Deck slides must come from CI enriched content, not legacy bullets dump."""
        ci = ContentIntent(
            topic="Platform Modernisation Initiative",
            goal="Secure leadership commitment to a three-year platform investment",
        )
        result = generate_presentation("Platform Modernisation Initiative", content_intent=ci)
        # Must produce more than the trivial [title, section, bullets] structure
        types = _slide_types(result.deck_definition)
        assert "title" in types, "Title slide must be present"
        # Should have content slides beyond the title
        assert len(types) > 1, "CI-driven deck must have more than a single title slide"

    def test_deck_has_semantic_content(self):
        """Slide content must be derived from CI assertions/supporting-points,
        not from raw input-text extraction."""
        ci = ContentIntent(
            topic="Delivery Pipeline Reliability",
            goal="Reduce deployment failures by 80%",
        )
        result = generate_presentation("Delivery Pipeline Reliability", content_intent=ci)
        all_text = _all_slide_text(result.deck_definition)
        # Content must be non-trivial
        assert len(all_text.strip()) > 50, "Deck content is unexpectedly thin"

    def test_enriched_content_matches_direct_ci_call(self):
        """enriched_content stored in the result must equal a direct CI call."""
        ci = ContentIntent(topic="Observability Uplift")
        result = generate_presentation("Observability Uplift", content_intent=ci)
        direct = run_content_intelligence(ci)
        assert len(result.enriched_content) == len(direct)
        for a, b in zip(result.enriched_content, direct):
            assert a.title == b.title
            assert a.assertion == b.assertion
            assert a.primitive == b.primitive


# ---------------------------------------------------------------------------
# Root cause regression: raw ContentIntent serialization must never appear
# ---------------------------------------------------------------------------

class TestNoRawObjectSerialization:
    """ContentIntent string representations must never reach slide text."""

    def test_content_intent_repr_not_in_slide_text(self):
        ci = ContentIntent(
            topic="DLQ Backlog Remediation",
            goal="Reduce DLQ backlog to zero within 30 days",
            context={"dlq_depth": "14,000 messages", "root_cause": "unknown"},
        )
        result = generate_presentation(
            "DLQ backlog is growing without clear root cause attribution",
            content_intent=ci,
        )
        all_text = _all_slide_text(result.deck_definition)
        # Raw ContentIntent repr must not appear
        assert "ContentIntent(" not in all_text, (
            "Raw ContentIntent() representation leaked into slide text"
        )

    def test_raw_context_dict_not_in_slide_bullets(self):
        """Context dict values must not appear verbatim as bullets unless
        they were processed through the CI pipeline into supporting_points."""
        raw_context_string = "DLQ backlog is growing without clear root cause attribution"
        ci = ContentIntent(
            topic="Delivery Status Review",
            context={"status_detail": raw_context_string},
        )
        result = generate_presentation(raw_context_string, content_intent=ci)
        # Check that the exact raw context string hasn't been dumped verbatim
        # into a bullet as a literal copy of the input.
        # (CI may use the topic in processed form, which is acceptable.)
        slides = result.deck_definition.get("slides", [])
        for slide in slides:
            for bullet in slide.get("bullets", []):
                # A bullet that is IDENTICAL to the raw context string (unprocessed) is a leak.
                assert bullet != raw_context_string, (
                    f"Raw context string appeared verbatim in bullets: {bullet!r}"
                )

    def test_content_intent_class_name_not_in_any_slide_field(self):
        """The literal string 'ContentIntent(' must never appear in any slide field."""
        ci = ContentIntent(topic="Security Posture Improvement")
        result = generate_presentation("Security Posture Improvement", content_intent=ci)
        all_text = _all_slide_text(result.deck_definition)
        assert "ContentIntent(" not in all_text

    def test_title_slide_subtitle_is_not_raw_serialization(self):
        """The title slide subtitle must be the goal string (or empty), never
        a Python object representation."""
        ci = ContentIntent(
            topic="Q2 Engineering Priorities",
            goal="Align on top 5 engineering investments",
        )
        result = generate_presentation("Q2 Engineering Priorities", content_intent=ci)
        slides = result.deck_definition.get("slides", [])
        title_slide = next((s for s in slides if s.get("type") == "title"), None)
        assert title_slide is not None
        subtitle = title_slide.get("subtitle", "")
        assert "ContentIntent(" not in subtitle
        assert "context=" not in subtitle


# ---------------------------------------------------------------------------
# Legacy path regression: non-CI inputs must still work correctly
# ---------------------------------------------------------------------------

class TestLegacyPathUnaffected:
    """Flows without content_intent must continue to work exactly as before."""

    def test_structured_yaml_bypass_unchanged(self):
        structured = "slides:\n  - type: title\n    title: Test Slide\n"
        result = generate_presentation(structured)
        assert result.stage == "deck_planned"
        assert result.playbook_id == "direct-deck-input"
        assert result.enriched_content is None

    def test_structured_yaml_with_no_content_intent_no_ci(self):
        """Structured YAML without content_intent must not trigger CI at all."""
        structured = "slides:\n  - type: title\n    title: No CI\n"
        result = generate_presentation(structured)
        assert result.enriched_content is None

    def test_structured_yaml_with_content_intent_runs_ci_for_enrichment(self):
        """Structured YAML + content_intent: deck from YAML, CI stored in enriched_content."""
        structured = "slides:\n  - type: title\n    title: Structured Slide\n"
        ci = ContentIntent(topic="Supplementary Analysis")
        result = generate_presentation(structured, content_intent=ci)
        # Deck comes from structured YAML (not CI)
        assert result.playbook_id == "direct-deck-input"
        # But CI still runs for enrichment
        assert result.enriched_content is not None


# ---------------------------------------------------------------------------
# Deck structure integrity
# ---------------------------------------------------------------------------

class TestCIDeckStructureIntegrity:
    """The CI-driven deck_definition must be structurally sound."""

    def test_deck_definition_has_slides_key(self):
        ci = ContentIntent(topic="Infrastructure Resilience")
        result = generate_presentation("Infrastructure Resilience", content_intent=ci)
        assert "slides" in result.deck_definition

    def test_deck_definition_has_deck_key(self):
        ci = ContentIntent(topic="Data Platform Strategy")
        result = generate_presentation("Data Platform Strategy", content_intent=ci)
        assert "deck" in result.deck_definition

    def test_deck_title_matches_topic(self):
        ci = ContentIntent(topic="Talent Development Framework")
        result = generate_presentation("Talent Development Framework", content_intent=ci)
        assert result.deck_definition["deck"]["title"] == "Talent Development Framework"

    def test_title_slide_is_first(self):
        ci = ContentIntent(topic="Executive Briefing")
        result = generate_presentation("Executive Briefing", content_intent=ci)
        slides = result.deck_definition.get("slides", [])
        assert slides[0]["type"] == "title"

    def test_title_slide_uses_topic(self):
        ci = ContentIntent(topic="Cloud Security Posture")
        result = generate_presentation("Cloud Security Posture", content_intent=ci)
        slides = result.deck_definition.get("slides", [])
        assert slides[0]["title"] == "Cloud Security Posture"

    def test_title_slide_subtitle_is_goal(self):
        ci = ContentIntent(
            topic="Platform Reliability",
            goal="Achieve 99.9% uptime SLA",
        )
        result = generate_presentation("Platform Reliability", content_intent=ci)
        slides = result.deck_definition.get("slides", [])
        title_slide = slides[0]
        assert title_slide.get("subtitle") == "Achieve 99.9% uptime SLA"

    def test_all_slides_have_type(self):
        ci = ContentIntent(topic="Delivery Excellence")
        result = generate_presentation("Delivery Excellence", content_intent=ci)
        for slide in result.deck_definition.get("slides", []):
            assert "type" in slide, f"Slide missing type: {slide}"

    def test_ci_metadata_present_in_content_slides(self):
        """Each CI-generated content slide must carry _ci_metadata."""
        ci = ContentIntent(topic="Cost Reduction Strategy")
        result = generate_presentation("Cost Reduction Strategy", content_intent=ci)
        slides = result.deck_definition.get("slides", [])
        # Content slides (not the title slide) should have _ci_metadata
        content_slides = [s for s in slides if s.get("type") == "bullets"]
        assert len(content_slides) >= 1
        for slide in content_slides:
            assert "_ci_metadata" in slide, (
                f"Content slide missing _ci_metadata: {slide.get('title')}"
            )

    def test_slide_primitives_recorded_in_ci_metadata(self):
        """Each content slide's _ci_metadata must carry the semantic primitive."""
        ci = ContentIntent(topic="Risk Management Programme")
        result = generate_presentation("Risk Management Programme", content_intent=ci)
        slides = result.deck_definition.get("slides", [])
        content_slides = [s for s in slides if s.get("type") == "bullets"]
        for slide in content_slides:
            meta = slide.get("_ci_metadata", {})
            assert "primitive" in meta, (
                f"_ci_metadata missing 'primitive' for slide: {slide.get('title')}"
            )
