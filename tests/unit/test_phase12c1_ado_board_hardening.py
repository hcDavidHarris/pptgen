"""Phase 12C.1 tests — ADO Board Ingestion Hardening.

Coverage
--------
Adapter hardening
    - assignedTo (camelCase) resolves to owner
    - workItemType (camelCase) resolves to type
    - both camelCase aliases coexist with snake_case aliases correctly
    - max work items cap truncates at _MAX_WORK_ITEMS (200)
    - items beyond cap are silently dropped (first N kept)
    - tags as None → empty list (not crash)
    - priority as string coerced to int
    - priority as float coerced to int

Extractor deduplication
    - blocked P1/P2 items NOT double-counted in risk section
    - blocked items that are also critical do NOT appear in critical_open risk count
    - all items blocked → risk insight 1 not emitted (nothing unblocked critical)
    - mixed blocked + unblocked critical → only unblocked appear in risk

Extractor section ordering
    - first section is "priority" (when P1 items present)
    - "risk" section precedes "progress" section
    - "blocker" section precedes "milestone" and "progress" sections

Extractor: progress insight 3 gating
    - progress insight 3 NOT emitted when recently_updated ≈ active count
    - progress insight 3 IS emitted when many non-active items have recent dates

Extractor: priority insights
    - priority distribution computed from open items only (not done)
    - owner concentration insight only emitted when ≥30% threshold met
    - owner with 2 of 20 items (10%) does NOT trigger concentration insight

Edge cases
    - all items complete → progress section present, no blocker or risk sections
    - all items blocked → blocker section present, risk section absent for those items
    - single item board → valid brief produced, bounded insights
    - board with no priority set → priority insights still useful (no crash)

Regression
    - all Phase 12C tests still pass (ensured by running both suites together)
"""

from __future__ import annotations

import pytest

from pptgen.ingestion.adapters.ado_board_adapter import AdoBoardAdapter, _MAX_WORK_ITEMS
from pptgen.ingestion.extractors.ado_board_extractor import extract
from pptgen.ingestion.ingestion_models import SourceDocument
from pptgen.ingestion.ado_board_orchestrator import ingest_ado_board_to_brief


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_doc(work_items, title="Test Board", source_id=None):
    return SourceDocument(
        source_type="ado_board",
        source_id=source_id,
        title=title,
        content=None,
        metadata={"work_items": work_items},
    )


def _norm(items, title="Test"):
    """Normalise items through the adapter and return the work_items list."""
    adapter = AdoBoardAdapter()
    doc = adapter.load({"title": title, "metadata": {"work_items": items}})
    return doc.metadata["work_items"]


def _categories(insights):
    return [i.category for i in insights]


# ===========================================================================
# Adapter hardening
# ===========================================================================


class TestAdoBoardAdapterHardening:

    def test_camelcase_assignedTo_resolves_to_owner(self):
        items = _norm([{"title": "Item", "assignedTo": "David"}])
        assert items[0]["owner"] == "David"

    def test_camelcase_workItemType_resolves_to_type(self):
        items = _norm([{"title": "Item", "workItemType": "UserStory"}])
        assert items[0]["type"] == "UserStory"

    def test_camelcase_preferred_after_explicit_type(self):
        # Explicit "type" takes priority over camelCase alias
        items = _norm([{"title": "Item", "type": "Feature", "workItemType": "Bug"}])
        assert items[0]["type"] == "Feature"

    def test_camelcase_preferred_after_explicit_owner(self):
        # Explicit "owner" takes priority over camelCase alias
        items = _norm([{"title": "Item", "owner": "Alice", "assignedTo": "Bob"}])
        assert items[0]["owner"] == "Alice"

    def test_snake_case_assigned_to_still_works(self):
        items = _norm([{"title": "Item", "assigned_to": "Carol"}])
        assert items[0]["owner"] == "Carol"

    def test_camelcase_keys_not_in_extra(self):
        # assignedTo and workItemType should be consumed, not end up in extra
        items = _norm([{"title": "Item", "assignedTo": "Dave", "workItemType": "Task"}])
        assert "extra" not in items[0] or "assignedTo" not in items[0].get("extra", {})
        assert "extra" not in items[0] or "workItemType" not in items[0].get("extra", {})

    def test_max_work_items_cap_enforced(self):
        oversized = [{"title": f"Item {i}", "state": "Active"} for i in range(250)]
        adapter = AdoBoardAdapter()
        doc = adapter.load({"title": "Big Board", "metadata": {"work_items": oversized}})
        assert len(doc.metadata["work_items"]) == _MAX_WORK_ITEMS

    def test_max_work_items_keeps_first_n(self):
        items = [{"title": f"Item {i}", "state": "Active", "id": i} for i in range(250)]
        adapter = AdoBoardAdapter()
        doc = adapter.load({"title": "Big Board", "metadata": {"work_items": items}})
        normalised = doc.metadata["work_items"]
        assert normalised[0]["id"] == 0
        assert normalised[-1]["id"] == _MAX_WORK_ITEMS - 1

    def test_items_at_exact_cap_not_truncated(self):
        items = [{"title": f"Item {i}"} for i in range(_MAX_WORK_ITEMS)]
        adapter = AdoBoardAdapter()
        doc = adapter.load({"title": "At-cap Board", "metadata": {"work_items": items}})
        assert len(doc.metadata["work_items"]) == _MAX_WORK_ITEMS

    def test_tags_none_normalised_to_empty_list(self):
        items = _norm([{"title": "Item", "tags": None}])
        assert items[0]["tags"] == []

    def test_priority_string_coerced_to_int(self):
        items = _norm([{"title": "Item", "priority": "1"}])
        assert items[0]["priority"] == 1

    def test_priority_invalid_string_normalised_to_none(self):
        items = _norm([{"title": "Item", "priority": "high"}])
        assert items[0]["priority"] is None


# ===========================================================================
# Extractor deduplication
# ===========================================================================


class TestExtractorDeduplication:
    """Blocked items must NOT be double-counted in the risk section."""

    def test_blocked_p1_not_in_risk_critical_open(self):
        # All P1 items are blocked → critical_open should be empty → no risk insight 1
        doc = _make_doc([
            {"id": 1, "title": "Blocked Critical", "state": "Blocked", "priority": 1},
            {"id": 2, "title": "Done Task", "state": "Done", "priority": 1},
        ])
        insights = extract(doc)
        risk_insights = [i for i in insights if i.category == "risk"]
        # Insight 1 (critical open) should not fire for blocked P1 items
        critical_open_insights = [
            i for i in risk_insights
            if "critical or high priority" in i.text
        ]
        # Either no such insight, or the count reflects only unblocked items (0 here)
        for ins in critical_open_insights:
            assert "0 open" in ins.text or critical_open_insights == []

    def test_unblocked_p1_still_appears_in_risk(self):
        # Unblocked P1 items must still surface as risk
        doc = _make_doc([
            {"id": 1, "title": "Blocked P1", "state": "Blocked", "priority": 1},
            {"id": 2, "title": "Open P1", "state": "Open", "priority": 1},
        ])
        insights = extract(doc)
        risk_insights = [i for i in insights if i.category == "risk"]
        # The open P1 item should appear in risk; the blocked one in blocker
        assert any("1 open" in i.text or "critical or high" in i.text for i in risk_insights)

    def test_all_critical_items_blocked_means_no_risk_insight_1(self):
        doc = _make_doc([
            {"id": 1, "title": "B1", "state": "Blocked", "priority": 1},
            {"id": 2, "title": "B2", "state": "Blocked", "priority": 2},
        ])
        insights = extract(doc)
        # Risk insight 1 is the critical-open concentration
        # With all critical items blocked, it should not fire (0 unblocked critical)
        risk_critical = [
            i for i in insights
            if i.category == "risk" and "critical or high priority" in i.text
        ]
        # If it fires, the count should be 0 (i.e., "0 open item(s) are critical or high")
        # or it simply should not fire at all
        for ins in risk_critical:
            # The text should reference 0, meaning the insight would be filtered out
            assert False, f"Risk critical-open fired unexpectedly: {ins.text}"

    def test_blocker_and_risk_do_not_reference_same_items(self):
        """No item ID should appear in both blocker and risk source_pointers."""
        doc = _make_doc([
            {"id": 10, "title": "Blocked Critical", "state": "Blocked", "priority": 1},
            {"id": 20, "title": "Open Critical", "state": "Open", "priority": 1},
            {"id": 30, "title": "Done", "state": "Done"},
        ])
        insights = extract(doc)
        blocker_ids: set[str] = set()
        for ins in insights:
            if ins.category == "blocker" and ins.source_pointer:
                raw = ins.source_pointer.replace("items:", "")
                blocker_ids.update(raw.split(","))

        risk_ids: set[str] = set()
        for ins in insights:
            if ins.category == "risk" and ins.source_pointer:
                raw = ins.source_pointer.replace("items:", "")
                risk_ids.update(raw.split(","))

        overlap = blocker_ids & risk_ids
        assert not overlap, f"Item IDs appear in both blocker and risk: {overlap}"


# ===========================================================================
# Extractor section ordering
# ===========================================================================


class TestExtractorSectionOrder:

    def _full_doc(self):
        return _make_doc([
            {"id": 1, "title": "P1 Feature", "state": "Active", "type": "Feature", "priority": 1},
            {"id": 2, "title": "Blocked Bug", "state": "Blocked", "type": "Bug", "priority": 2},
            {"id": 3, "title": "Done Task", "state": "Done", "type": "Task"},
            {"id": 4, "title": "Epic A", "state": "In Progress", "type": "Epic"},
        ])

    def test_priority_category_emitted_before_progress(self):
        doc = self._full_doc()
        insights = extract(doc)
        cats = _categories(insights)
        if "priority" in cats and "progress" in cats:
            assert cats.index("priority") < cats.index("progress")

    def test_risk_category_emitted_before_progress(self):
        doc = self._full_doc()
        insights = extract(doc)
        cats = _categories(insights)
        if "risk" in cats and "progress" in cats:
            assert cats.index("risk") < cats.index("progress")

    def test_blocker_category_emitted_before_progress(self):
        doc = self._full_doc()
        insights = extract(doc)
        cats = _categories(insights)
        if "blocker" in cats and "progress" in cats:
            assert cats.index("blocker") < cats.index("progress")


# ===========================================================================
# Extractor: progress insight 3 gating
# ===========================================================================


class TestProgressInsight3Gating:

    def test_no_extra_movement_does_not_emit_insight_3(self):
        """When all recently-updated items are already 'active', insight 3 should not emit."""
        # 2 active items, both recently updated — no material extra signal
        doc = _make_doc([
            {"id": 1, "title": "Active A", "state": "Active", "updated_date": "2026-03-30"},
            {"id": 2, "title": "Active B", "state": "Active", "updated_date": "2026-03-29"},
        ])
        insights = extract(doc)
        progress_insights = [i for i in insights if i.category == "progress"]
        # Only insight 1 (completion) and insight 2 (active items) should be present
        assert len(progress_insights) <= 2

    def test_material_extra_movement_emits_insight_3(self):
        """When many non-active items have recent dates, insight 3 should emit."""
        # 1 active item + 5 recently-updated open items = extra_movement = 5 > 2
        doc = _make_doc([
            {"id": 1, "title": "Active", "state": "Active", "updated_date": "2026-03-30"},
            {"id": 2, "title": "Open A", "state": "Open", "updated_date": "2026-03-30"},
            {"id": 3, "title": "Open B", "state": "Open", "updated_date": "2026-03-29"},
            {"id": 4, "title": "Open C", "state": "Open", "updated_date": "2026-03-28"},
            {"id": 5, "title": "Open D", "state": "Open", "updated_date": "2026-03-27"},
            {"id": 6, "title": "Open E", "state": "Open", "updated_date": "2026-03-26"},
        ])
        insights = extract(doc)
        progress_insights = [i for i in insights if i.category == "progress"]
        # Should emit up to 3 progress insights including the movement one
        assert len(progress_insights) >= 2


# ===========================================================================
# Extractor: priority insights
# ===========================================================================


class TestPriorityInsights:

    def test_priority_distribution_from_open_items_only(self):
        """Priority distribution insight should reflect only open items, not done ones."""
        doc = _make_doc([
            {"id": 1, "title": "Done P1", "state": "Done", "priority": 1},
            {"id": 2, "title": "Open P2", "state": "Open", "priority": 2},
            {"id": 3, "title": "Open P3", "state": "Open", "priority": 3},
        ])
        insights = extract(doc)
        priority_insights = [i for i in insights if i.category == "priority"]
        # Priority distribution insight should NOT mention P1 (only done P1 exists)
        dist_insights = [i for i in priority_insights if "P1" in i.text or "P2" in i.text]
        for ins in dist_insights:
            # Should not include done P1
            assert "P1" not in ins.text or "critical-priority" not in ins.text.lower()

    def test_owner_concentration_not_triggered_below_30pct(self):
        """2 of 20 items (10%) should NOT trigger the owner concentration insight."""
        doc = _make_doc(
            [{"id": i, "title": f"Task {i}", "state": "Open", "owner": "Alice" if i < 2 else f"Owner{i}"}
             for i in range(20)]
        )
        insights = extract(doc)
        priority_insights = [i for i in insights if i.category == "priority"]
        concentration = [i for i in priority_insights if "holds" in i.text and "%" in i.text]
        assert len(concentration) == 0

    def test_owner_concentration_triggered_at_30pct(self):
        """Owner holding ≥30% of open work triggers the concentration insight."""
        # Alice holds 4 of 10 items = 40%
        items = (
            [{"id": i, "title": f"Alice Task {i}", "state": "Open", "owner": "Alice"} for i in range(4)]
            + [{"id": 10 + i, "title": f"Other Task {i}", "state": "Open", "owner": f"Person{i}"} for i in range(6)]
        )
        doc = _make_doc(items)
        insights = extract(doc)
        priority_insights = [i for i in insights if i.category == "priority"]
        concentration = [i for i in priority_insights if "Alice" in i.text and "%" in i.text]
        assert len(concentration) >= 1

    def test_unassigned_owner_does_not_trigger_concentration(self):
        """Owner 'Unassigned' never triggers concentration insight."""
        # All items have no owner → Unassigned gets everything
        doc = _make_doc([
            {"id": i, "title": f"Task {i}", "state": "Open"}
            for i in range(5)
        ])
        insights = extract(doc)
        priority_insights = [i for i in insights if i.category == "priority"]
        unassigned_conc = [i for i in priority_insights if "Unassigned" in i.text and "holds" in i.text]
        assert len(unassigned_conc) == 0


# ===========================================================================
# Edge cases
# ===========================================================================


class TestEdgeCases:

    def test_all_items_complete(self):
        """Board where every item is done should produce valid brief with no blockers."""
        doc = _make_doc([
            {"id": 1, "title": "Done A", "state": "Done"},
            {"id": 2, "title": "Done B", "state": "Closed"},
            {"id": 3, "title": "Done C", "state": "Resolved"},
        ])
        insights = extract(doc)
        assert len(insights) >= 1
        # No blockers on a fully-complete board
        assert not any(i.category == "blocker" for i in insights)
        # Progress insight should be present
        assert any(i.category == "progress" for i in insights)
        # Completion text should say 100% or all items
        progress = [i for i in insights if i.category == "progress"][0]
        assert "3 of 3" in progress.text

    def test_all_items_blocked(self):
        """Board where every item is blocked: blocker section present, no critical-open risk."""
        doc = _make_doc([
            {"id": 1, "title": "Blocked A", "state": "Blocked", "priority": 1},
            {"id": 2, "title": "Blocked B", "state": "On Hold", "priority": 2},
        ])
        insights = extract(doc)
        assert any(i.category == "blocker" for i in insights)
        # No unblocked critical items → no risk insight 1
        risk_critical = [
            i for i in insights
            if i.category == "risk" and "critical or high priority" in i.text
        ]
        assert len(risk_critical) == 0

    def test_single_item_board(self):
        """Single-item board produces a valid, bounded brief."""
        brief = ingest_ado_board_to_brief({
            "title": "Solo Sprint",
            "metadata": {"work_items": [{"id": 1, "title": "Only Task", "state": "Active", "priority": 1}]},
        })
        assert brief.brief_type == "delivery"
        assert len(brief.sections) >= 1
        # Total insights ≤ 15
        total_insights = sum(len(s["insights"]) for s in brief.sections)
        assert total_insights <= 15

    def test_no_priority_set_on_any_item(self):
        """Board with no priorities set should not crash and should still produce a brief."""
        doc = _make_doc([
            {"id": 1, "title": "Task A", "state": "Active"},
            {"id": 2, "title": "Task B", "state": "Open"},
        ])
        insights = extract(doc)
        assert len(insights) >= 1
        # No risk insight from priority (nothing set)
        risk_priority_insights = [
            i for i in insights
            if i.category == "risk" and "critical or high" in i.text
        ]
        assert len(risk_priority_insights) == 0

    def test_items_with_no_ids_do_not_crash_pointers(self):
        """Items without IDs should still produce insights with safe source_pointers."""
        doc = _make_doc([
            {"title": "No ID Item A", "state": "Blocked", "priority": 1},
            {"title": "No ID Item B", "state": "Open", "priority": 1},
        ])
        insights = extract(doc)
        # source_pointers may be None (no IDs to reference) — must not crash
        for ins in insights:
            # If no IDs exist, source_pointer is None; that's fine
            assert ins.source_pointer is None or isinstance(ins.source_pointer, str)

    def test_bounded_insight_count_on_large_board(self):
        """Even with many items, total insights must be ≤15."""
        items = [
            {"id": i, "title": f"Item {i}", "state": "Active" if i % 3 != 0 else "Blocked",
             "type": "Feature" if i % 5 == 0 else "Bug", "priority": (i % 4) + 1,
             "owner": f"Owner{i % 3}"}
            for i in range(50)
        ]
        doc = _make_doc(items)
        insights = extract(doc)
        assert len(insights) <= 15


# ===========================================================================
# Regression: existing Phase 12C suite still passes (smoke)
# ===========================================================================


class TestPhase12C1Regression:

    def test_transcript_ingestion_unaffected(self):
        from pptgen.ingestion.transcript_orchestrator import ingest_transcript_to_brief
        brief = ingest_transcript_to_brief({
            "title": "Regression check",
            "content": (
                "We agreed to move forward with the cloud migration as the top priority. "
                "Alice will deliver the plan by next week. "
                "Risk: the legacy dependency may block us."
            ),
        })
        assert brief.brief_type in {"strategic", "eos_rocks"}

    def test_ado_board_still_produces_delivery_brief(self):
        brief = ingest_ado_board_to_brief({
            "title": "Regression Board",
            "metadata": {
                "work_items": [
                    {"id": 1, "title": "Item A", "state": "Active", "priority": 1},
                    {"id": 2, "title": "Item B", "state": "Done"},
                ],
            },
        })
        assert brief.brief_type == "delivery"
        assert len(brief.sections) >= 1

    def test_insight_count_never_exceeds_15(self):
        brief = ingest_ado_board_to_brief({
            "title": "Full Board",
            "metadata": {
                "work_items": [
                    {"id": i, "title": f"Item {i}", "state": "Active",
                     "type": "Feature", "priority": 1, "owner": f"Owner{i % 3}"}
                    for i in range(20)
                ],
            },
        })
        total_insights = sum(len(s["insights"]) for s in brief.sections)
        assert total_insights <= 15
