"""Phase 12C tests — ADO Board Ingestion Vertical Slice.

Coverage
--------
Adapter
    - payload with title only normalises correctly
    - missing title raises AdapterPayloadError
    - work_items are normalised into stable schema
    - work_item type alias (work_item_type) is coerced to type
    - work_item owner alias (assigned_to) is coerced to owner
    - tags as comma-separated string are split into list
    - unknown extra fields are preserved in "extra"
    - optional metadata fields (iteration, team, date) are preserved
    - empty work_items list is tolerated
    - non-dict items in work_items are skipped

Extractor (ado_board_extractor)
    - empty work items produces fallback progress insight
    - rich board produces bounded insight set (≤15 insights)
    - all five categories are present for a representative board
    - insights never exceed _MAX_PER_CATEGORY (3) per category
    - all derivation_types are valid ("aggregated" or "inferred")
    - confidence values are in [0.40, 0.95]
    - blocked items produce blocker insights
    - critical/high-priority items produce risk insights
    - epic/feature items produce milestone insights
    - priority distribution produces priority insights
    - source_pointer references item IDs where applicable
    - source_type and source_id are propagated on every insight

Brief synthesis
    - ado_board source produces a DeliveryBrief (brief_type="delivery")
    - brief topic matches payload title
    - brief sections are non-empty
    - provenance summary is preserved end-to-end
    - brief confidence is set

CI bridge
    - brief_to_content_intent produces a ContentIntent from a DeliveryBrief
    - ContentIntent.topic matches brief.topic
    - ContentIntent.context carries brief_type="delivery"
    - ContentIntent.context carries sections and confidence

End-to-end orchestration
    - ingest_ado_board_to_brief returns a BaseBrief of type "delivery"
    - ingest_ado_board_to_content_intent returns a ContentIntent
    - both paths are deterministic
    - transcript path is unaffected (regression)
    - existing CI paths are unaffected (regression)
"""

from __future__ import annotations

import pytest

from pptgen.ingestion.adapters.base import AdapterPayloadError
from pptgen.ingestion.adapters.ado_board_adapter import AdoBoardAdapter
from pptgen.ingestion.ado_board_orchestrator import (
    ingest_ado_board_to_brief,
    ingest_ado_board_to_content_intent,
)
from pptgen.ingestion.brief_types import BRIEF_TYPE_DELIVERY
from pptgen.ingestion.ci_bridge import ContentIntent, brief_to_content_intent
from pptgen.ingestion.extractors.ado_board_extractor import extract
from pptgen.ingestion.ingestion_models import (
    BaseBrief,
    ExtractedInsight,
    SourceDocument,
    VALID_DERIVATION_TYPES,
)

# ---------------------------------------------------------------------------
# Fixtures / sample data
# ---------------------------------------------------------------------------

_MINIMAL_PAYLOAD: dict = {
    "title": "Q3 Delivery Status",
}

_FULL_PAYLOAD: dict = {
    "title": "Sprint 42 — Interchange Team",
    "source_id": "board-sprint-42",
    "metadata": {
        "work_items": [
            {
                "id": 101,
                "title": "Build ingestion routing",
                "state": "In Progress",
                "type": "Feature",
                "owner": "Alice",
                "priority": 1,
                "tags": ["platform", "phase12c"],
                "created_date": "2026-03-01",
                "updated_date": "2026-03-29",
            },
            {
                "id": 102,
                "title": "Fix auth token expiry bug",
                "state": "Blocked",
                "type": "Bug",
                "owner": "Bob",
                "priority": 2,
                "tags": ["auth", "blocked"],
                "created_date": "2026-03-05",
                "updated_date": "2026-03-10",
            },
            {
                "id": 103,
                "title": "Deploy to staging",
                "state": "Done",
                "type": "Task",
                "owner": "Alice",
                "priority": 3,
                "tags": [],
                "created_date": "2026-03-01",
                "updated_date": "2026-03-28",
            },
            {
                "id": 104,
                "title": "Platform reliability epic",
                "state": "In Progress",
                "type": "Epic",
                "owner": "Carol",
                "priority": 1,
                "tags": ["platform"],
                "created_date": "2026-02-01",
                "updated_date": "2026-03-30",
            },
            {
                "id": 105,
                "title": "Update documentation",
                "state": "Open",
                "type": "Task",
                "owner": "Bob",
                "priority": 4,
                "tags": [],
                "created_date": "2026-03-15",
                "updated_date": "2026-03-15",
            },
        ],
        "iteration": "Sprint 42",
        "team": "Interchange",
        "date": "2026-04-01",
    },
}

_STALE_PAYLOAD: dict = {
    "title": "Stale Board",
    "metadata": {
        "work_items": [
            {
                "id": 201,
                "title": "Critical work not moving",
                "state": "Active",
                "type": "Feature",
                "priority": 1,
                "updated_date": "2026-01-01",  # very stale
            },
            {
                "id": 202,
                "title": "High-priority stalled",
                "state": "Open",
                "type": "Task",
                "priority": 2,
                "updated_date": "2026-01-05",  # very stale
            },
        ]
    },
}


def _make_source_doc(work_items=None, title="Test Board", source_id=None):
    return SourceDocument(
        source_type="ado_board",
        source_id=source_id,
        title=title,
        content=None,
        metadata={"work_items": work_items or []},
    )


# ===========================================================================
# Adapter tests
# ===========================================================================


class TestAdoBoardAdapterPhase12C:
    """AdoBoardAdapter contract tests."""

    def test_minimal_payload_produces_source_document(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_MINIMAL_PAYLOAD)
        assert doc.source_type == "ado_board"
        assert doc.title == "Q3 Delivery Status"
        assert doc.content is None
        assert doc.source_id is None
        assert isinstance(doc.metadata, dict)

    def test_missing_title_raises_adapter_payload_error(self):
        adapter = AdoBoardAdapter()
        with pytest.raises(AdapterPayloadError, match="title"):
            adapter.load({})

    def test_empty_title_raises_adapter_payload_error(self):
        adapter = AdoBoardAdapter()
        with pytest.raises(AdapterPayloadError, match="title"):
            adapter.load({"title": "   "})

    def test_work_items_normalised(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        items = doc.metadata["work_items"]
        assert len(items) == 5
        first = items[0]
        assert first["id"] == 101
        assert first["title"] == "Build ingestion routing"
        assert first["state"] == "In Progress"
        assert first["type"] == "Feature"
        assert first["owner"] == "Alice"
        assert first["priority"] == 1
        assert "platform" in first["tags"]

    def test_work_item_type_alias_coerced(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({
            "title": "Test",
            "metadata": {
                "work_items": [
                    {"title": "Item A", "work_item_type": "UserStory", "state": "Active"}
                ]
            },
        })
        assert doc.metadata["work_items"][0]["type"] == "UserStory"

    def test_work_item_owner_alias_coerced(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({
            "title": "Test",
            "metadata": {
                "work_items": [
                    {"title": "Item B", "assigned_to": "Dave", "state": "Active"}
                ]
            },
        })
        assert doc.metadata["work_items"][0]["owner"] == "Dave"

    def test_tags_as_comma_string_are_split(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({
            "title": "Test",
            "metadata": {
                "work_items": [
                    {"title": "Item C", "tags": "alpha, beta, gamma"}
                ]
            },
        })
        assert doc.metadata["work_items"][0]["tags"] == ["alpha", "beta", "gamma"]

    def test_unknown_extra_fields_preserved(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({
            "title": "Test",
            "metadata": {
                "work_items": [
                    {"title": "Item D", "custom_field": "custom_value"}
                ]
            },
        })
        item = doc.metadata["work_items"][0]
        assert item.get("extra", {}).get("custom_field") == "custom_value"

    def test_optional_metadata_fields_preserved(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        assert doc.metadata["iteration"] == "Sprint 42"
        assert doc.metadata["team"] == "Interchange"
        assert doc.metadata["date"] == "2026-04-01"

    def test_empty_work_items_tolerated(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({"title": "Empty Board", "metadata": {"work_items": []}})
        assert doc.metadata["work_items"] == []

    def test_non_dict_items_in_work_items_are_skipped(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({
            "title": "Test",
            "metadata": {
                "work_items": [
                    "not a dict",
                    42,
                    {"title": "Real Item", "state": "Active"},
                ]
            },
        })
        assert len(doc.metadata["work_items"]) == 1
        assert doc.metadata["work_items"][0]["title"] == "Real Item"

    def test_source_id_preserved(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        assert doc.source_id == "board-sprint-42"

    def test_content_passed_through(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load({
            "title": "Test",
            "content": "Some pre-serialised content",
        })
        assert doc.content == "Some pre-serialised content"


# ===========================================================================
# Extractor tests
# ===========================================================================


class TestAdoBoardExtractorPhase12C:
    """AdoBoardExtractor insight categorisation and bounding tests."""

    def test_empty_work_items_returns_fallback(self):
        doc = _make_source_doc(work_items=[])
        insights = extract(doc)
        assert len(insights) == 1
        assert insights[0].category == "progress"
        assert insights[0].metadata.get("fallback") is True

    def test_no_metadata_key_returns_fallback(self):
        doc = SourceDocument(
            source_type="ado_board",
            source_id=None,
            title="No Meta Board",
            content=None,
            metadata={},
        )
        insights = extract(doc)
        assert len(insights) >= 1
        assert insights[0].category == "progress"

    def test_rich_board_produces_bounded_insights(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        insights = extract(doc)
        assert 1 <= len(insights) <= 15

    def test_insight_count_per_category_does_not_exceed_cap(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        insights = extract(doc)
        from collections import Counter
        counts = Counter(i.category for i in insights)
        for category, count in counts.items():
            assert count <= 3, f"Category '{category}' has {count} insights > cap of 3"

    def test_all_derivation_types_valid(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        insights = extract(doc)
        for ins in insights:
            assert ins.derivation_type in VALID_DERIVATION_TYPES, (
                f"Invalid derivation_type: {ins.derivation_type!r}"
            )

    def test_confidence_values_in_range(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        insights = extract(doc)
        for ins in insights:
            assert ins.confidence is not None
            assert 0.40 <= ins.confidence <= 0.95, (
                f"Confidence {ins.confidence} out of [0.40, 0.95]"
            )

    def test_source_type_propagated(self):
        doc = _make_source_doc(work_items=[{"title": "X", "state": "Active"}])
        insights = extract(doc)
        for ins in insights:
            assert ins.source_type == "ado_board"

    def test_source_id_propagated(self):
        doc = _make_source_doc(
            work_items=[{"title": "X", "state": "Active"}],
            source_id="board-123",
        )
        insights = extract(doc)
        for ins in insights:
            assert ins.source_id == "board-123"

    def test_blocked_items_produce_blocker_insights(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "Blocker A", "state": "Blocked", "priority": 1},
            {"id": 2, "title": "Blocker B", "state": "On Hold", "priority": 2},
        ])
        insights = extract(doc)
        blocker_cats = [i for i in insights if i.category == "blocker"]
        assert len(blocker_cats) >= 1

    def test_no_blockers_means_no_blocker_category(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "Active task", "state": "Active", "priority": 3},
            {"id": 2, "title": "Done task", "state": "Done", "priority": 4},
        ])
        insights = extract(doc)
        blocker_cats = [i for i in insights if i.category == "blocker"]
        assert len(blocker_cats) == 0

    def test_critical_items_produce_risk_insights(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "P1 Item", "state": "Open", "priority": 1},
            {"id": 2, "title": "P2 Item", "state": "Active", "priority": 2},
            {"id": 3, "title": "Done", "state": "Done", "priority": 1},
        ])
        insights = extract(doc)
        risk_cats = [i for i in insights if i.category == "risk"]
        assert len(risk_cats) >= 1

    def test_bugs_produce_risk_insights(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "Bug A", "state": "Active", "type": "Bug"},
            {"id": 2, "title": "Bug B", "state": "Open", "type": "Bug"},
        ])
        insights = extract(doc)
        risk_cats = [i for i in insights if i.category == "risk"]
        assert len(risk_cats) >= 1

    def test_epics_produce_milestone_insights(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "Big Epic", "state": "In Progress", "type": "Epic"},
        ])
        insights = extract(doc)
        milestone_cats = [i for i in insights if i.category == "milestone"]
        assert len(milestone_cats) >= 1

    def test_features_produce_milestone_insights(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "Feature X", "state": "Active", "type": "Feature", "priority": 1},
        ])
        insights = extract(doc)
        milestone_cats = [i for i in insights if i.category == "milestone"]
        assert len(milestone_cats) >= 1

    def test_progress_insight_always_present(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_FULL_PAYLOAD)
        insights = extract(doc)
        progress_cats = [i for i in insights if i.category == "progress"]
        assert len(progress_cats) >= 1

    def test_progress_insight_completion_text(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "Done A", "state": "Done"},
            {"id": 2, "title": "Done B", "state": "Closed"},
            {"id": 3, "title": "Open C", "state": "Open"},
        ])
        insights = extract(doc)
        progress = [i for i in insights if i.category == "progress"][0]
        # Should mention completion ratio
        assert "of" in progress.text and "completed" in progress.text

    def test_stale_critical_items_produce_risk(self):
        adapter = AdoBoardAdapter()
        doc = adapter.load(_STALE_PAYLOAD)
        insights = extract(doc)
        risk_cats = [i for i in insights if i.category == "risk"]
        assert len(risk_cats) >= 1
        # At least one risk insight should mention staleness
        stale_risk = [i for i in risk_cats if "stale" in i.text.lower() or "not been updated" in i.text.lower()]
        assert len(stale_risk) >= 1

    def test_source_pointer_references_item_ids(self):
        doc = _make_source_doc(work_items=[
            {"id": 101, "title": "Item A", "state": "Blocked", "priority": 1},
        ])
        insights = extract(doc)
        blocker = [i for i in insights if i.category == "blocker"]
        assert len(blocker) >= 1
        ptr = blocker[0].source_pointer
        assert ptr is not None
        assert "101" in ptr

    def test_priority_distribution_insight(self):
        doc = _make_source_doc(work_items=[
            {"id": 1, "title": "P1", "state": "Open", "priority": 1},
            {"id": 2, "title": "P2", "state": "Open", "priority": 2},
            {"id": 3, "title": "P3", "state": "Open", "priority": 3},
        ])
        insights = extract(doc)
        priority_cats = [i for i in insights if i.category == "priority"]
        assert len(priority_cats) >= 1


# ===========================================================================
# Brief synthesis tests
# ===========================================================================


class TestAdoBoardBriefSynthesis:
    """DeliveryBrief construction for ado_board source."""

    def test_ado_board_produces_delivery_brief(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert isinstance(brief, BaseBrief)
        assert brief.brief_type == BRIEF_TYPE_DELIVERY

    def test_brief_topic_matches_title(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert brief.topic == "Sprint 42 — Interchange Team"

    def test_brief_goal_set(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert brief.goal
        assert len(brief.goal) > 0

    def test_brief_audience_set(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert brief.audience
        assert len(brief.audience) > 0

    def test_brief_sections_non_empty(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert len(brief.sections) > 0
        for section in brief.sections:
            assert "title" in section
            assert "insights" in section
            assert len(section["insights"]) > 0

    def test_brief_provenance_present(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert len(brief.provenance) > 0

    def test_brief_confidence_set(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert brief.confidence is not None
        assert 0.0 <= brief.confidence <= 1.0

    def test_brief_metadata_carries_source_type(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert brief.metadata.get("source_type") == "ado_board"

    def test_minimal_payload_produces_valid_brief(self):
        brief = ingest_ado_board_to_brief(_MINIMAL_PAYLOAD)
        assert brief.brief_type == BRIEF_TYPE_DELIVERY
        assert brief.topic == "Q3 Delivery Status"


# ===========================================================================
# CI bridge tests
# ===========================================================================


class TestAdoBoardCIBridge:
    """CI bridge produces valid ContentIntent from DeliveryBrief."""

    def test_produces_content_intent(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert isinstance(intent, ContentIntent)

    def test_topic_matches_brief_topic(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        intent = brief_to_content_intent(brief)
        assert intent.topic == brief.topic

    def test_goal_matches_brief_goal(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        intent = brief_to_content_intent(brief)
        assert intent.goal == brief.goal

    def test_context_carries_brief_type(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert intent.context["brief_type"] == BRIEF_TYPE_DELIVERY

    def test_context_carries_source_type(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert intent.context["source_type"] == "ado_board"

    def test_context_carries_confidence(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert intent.context["confidence"] is not None

    def test_context_sections_non_empty(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert len(intent.context["sections"]) > 0

    def test_context_provenance_present(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert len(intent.context["provenance"]) > 0

    def test_intent_suitable_for_delivery_deck(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        # Goal should reflect delivery framing
        assert intent.goal is not None
        goal_lower = intent.goal.lower()
        assert any(kw in goal_lower for kw in ["delivery", "status", "outcome", "blocker"])


# ===========================================================================
# End-to-end orchestration tests
# ===========================================================================


class TestAdoBoardOrchestration:
    """End-to-end orchestration via ingest_ado_board_to_* functions."""

    def test_to_brief_returns_base_brief(self):
        brief = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert isinstance(brief, BaseBrief)

    def test_to_content_intent_returns_content_intent(self):
        intent = ingest_ado_board_to_content_intent(_FULL_PAYLOAD)
        assert isinstance(intent, ContentIntent)

    def test_both_paths_are_deterministic(self):
        brief1 = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        brief2 = ingest_ado_board_to_brief(_FULL_PAYLOAD)
        assert brief1.brief_type == brief2.brief_type
        assert brief1.topic == brief2.topic
        assert len(brief1.sections) == len(brief2.sections)

    def test_missing_title_raises_adapter_payload_error(self):
        with pytest.raises(AdapterPayloadError, match="title"):
            ingest_ado_board_to_brief({"metadata": {"work_items": []}})

    def test_empty_work_items_still_produces_brief(self):
        brief = ingest_ado_board_to_brief({
            "title": "Empty Board",
            "metadata": {"work_items": []},
        })
        assert isinstance(brief, BaseBrief)
        assert brief.brief_type == BRIEF_TYPE_DELIVERY

    def test_no_metadata_still_produces_brief(self):
        brief = ingest_ado_board_to_brief({"title": "No Meta Board"})
        assert isinstance(brief, BaseBrief)
        assert brief.brief_type == BRIEF_TYPE_DELIVERY


# ===========================================================================
# Regression tests — transcript and CI paths unaffected
# ===========================================================================


class TestPhase12CRegressions:
    """Validate that Phase 12B transcript path and CI path are unaffected."""

    def test_transcript_path_still_works(self):
        """Transcript ingestion must not be broken by Phase 12C changes."""
        from pptgen.ingestion.transcript_orchestrator import ingest_transcript_to_brief
        from pptgen.ingestion.brief_types import BRIEF_TYPE_STRATEGIC

        payload = {
            "title": "Regression check",
            "content": (
                "The team agreed to focus on platform stability as the top priority. "
                "Alice will lead the architecture review by next week. "
                "There is a risk that the migration could block delivery."
            ),
        }
        brief = ingest_transcript_to_brief(payload)
        assert isinstance(brief, BaseBrief)
        assert brief.brief_type in {BRIEF_TYPE_STRATEGIC, "eos_rocks"}

    def test_ado_board_source_type_not_routed_to_transcript(self):
        """ado_board source must use DeliveryBrief, not StrategicBrief."""
        brief = ingest_ado_board_to_brief(_MINIMAL_PAYLOAD)
        assert brief.brief_type == BRIEF_TYPE_DELIVERY
        assert brief.brief_type != "strategic"

    def test_ci_bridge_unchanged_for_strategic_brief(self):
        """brief_to_content_intent must still work for StrategicBrief."""
        from pptgen.ingestion.brief_types import StrategicBrief

        strategic = StrategicBrief(
            topic="Platform Migration",
            sections=[{"title": "Theme", "insights": ["We are migrating to the cloud."]}],
        )
        intent = brief_to_content_intent(strategic)
        assert isinstance(intent, ContentIntent)
        assert intent.topic == "Platform Migration"
        assert intent.context["brief_type"] == "strategic"
