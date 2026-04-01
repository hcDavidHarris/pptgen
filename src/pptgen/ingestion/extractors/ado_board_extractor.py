"""Real extractor for Azure DevOps board sources (Phase 12C).

Replaces the stub extractor for source_type="ado_board".

Approach
--------
Rule-based heuristic extraction: deterministic, no LLM dependency.
Work items are read from ``source_document.metadata["work_items"]``
(normalised by AdoBoardAdapter).  Items are classified by state and
aggregated into 5 category buckets:

    progress  — delivery velocity and completion signal
    blocker   — items explicitly blocked or effectively stalled
    risk      — concentrations of open high-priority or buggy work
    milestone — epics / features representing key deliverables
    priority  — top focus areas by priority distribution

Bounding strategy
-----------------
Each category emits at most 3 insights (max 15 total).  Items are
aggregated rather than enumerated: many blocked items collapse into one
blocker insight; a high-priority concentration becomes a single risk
insight.  This keeps the output executive-ready, not a ticket dump.

Provenance
----------
- Each insight carries a ``source_pointer`` referencing item IDs
  (e.g. "items:101,102,103") so insights remain traceable.
- ``derivation_type`` is "aggregated" for statistical summaries and
  "inferred" for derived risk / milestone signals.
- Confidence is derived from signal strength and item count.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any

from ..ingestion_models import ExtractedInsight, SourceDocument

# ---------------------------------------------------------------------------
# State classification buckets
# ---------------------------------------------------------------------------

_DONE_STATES: frozenset[str] = frozenset(
    {"done", "closed", "resolved", "completed", "finished", "accepted"}
)
_ACTIVE_STATES: frozenset[str] = frozenset(
    {"active", "in progress", "in review", "testing", "committed", "development"}
)
_BLOCKED_STATES: frozenset[str] = frozenset(
    {"blocked", "on hold", "impediment", "waiting", "impeded"}
)
_BLOCKED_TAGS: frozenset[str] = frozenset(
    {"blocked", "blocker", "impediment", "on-hold"}
)

# Work item types that represent milestone-level deliverables.
_MILESTONE_TYPES: frozenset[str] = frozenset(
    {"epic", "feature", "initiative", "deliverable"}
)
_BUG_TYPES: frozenset[str] = frozenset(
    {"bug", "defect", "issue", "hotfix"}
)

# Priority values for critical / high work
_CRITICAL_PRIORITY = 1
_HIGH_PRIORITY = 2

# Staleness threshold in days (items not updated for this long are "stale")
_STALE_THRESHOLD_DAYS = 7

# Per-category insight caps
_MAX_PER_CATEGORY = 3

# Fallback for minimal / empty input
_FALLBACK_PROGRESS_TEXT = "Delivery status could not be determined: no work items provided."


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract(source_document: SourceDocument) -> list[ExtractedInsight]:
    """Extract structured insights from an ADO board source document.

    Args:
        source_document: A SourceDocument with source_type="ado_board".
                         Work items are read from
                         ``source_document.metadata["work_items"]``.

    Returns:
        A bounded list (≤15) of ExtractedInsight objects covering
        progress, blockers, risks, milestones, and priority focus areas.
    """
    items: list[dict[str, Any]] = source_document.metadata.get("work_items") or []

    if not items:
        return _fallback_insights(source_document)

    stats = _compute_stats(items, source_document)

    # Emit in executive-priority order: what requires action first, then status.
    insights: list[ExtractedInsight] = []
    insights.extend(_extract_priority(stats, source_document))
    insights.extend(_extract_risks(stats, source_document))
    insights.extend(_extract_blockers(stats, source_document))
    insights.extend(_extract_milestones(stats, source_document))
    insights.extend(_extract_progress(stats, source_document))

    return insights


# ---------------------------------------------------------------------------
# Statistics computation
# ---------------------------------------------------------------------------


def _compute_stats(
    items: list[dict[str, Any]],
    source_document: SourceDocument,
) -> dict[str, Any]:
    """Derive aggregated statistics from the normalised work item list."""
    total = len(items)
    today = _today()

    done: list[dict] = []
    active: list[dict] = []
    blocked: list[dict] = []
    open_: list[dict] = []

    for item in items:
        bucket = _classify_state(item.get("state", ""))
        if bucket == "done":
            done.append(item)
        elif bucket == "active":
            active.append(item)
        elif bucket == "blocked":
            blocked.append(item)
        else:
            open_.append(item)

    # Tag-based blocked items (not already in blocked bucket)
    tag_blocked = [
        i for i in active + open_
        if any(t.lower() in _BLOCKED_TAGS for t in (i.get("tags") or []))
    ]

    all_blocked = blocked + tag_blocked

    # Priority buckets (from open + active work)
    not_done = active + blocked + open_
    p1_items = [i for i in not_done if i.get("priority") == _CRITICAL_PRIORITY]
    p2_items = [i for i in not_done if i.get("priority") == _HIGH_PRIORITY]

    # Bug concentration
    bugs = [
        i for i in not_done
        if i.get("type", "").lower() in _BUG_TYPES
    ]

    # Milestone-type items (not done)
    milestone_items = [
        i for i in items
        if i.get("type", "").lower() in _MILESTONE_TYPES
    ]
    milestone_active = [i for i in milestone_items if _classify_state(i.get("state", "")) != "done"]
    milestone_done = [i for i in milestone_items if _classify_state(i.get("state", "")) == "done"]

    # Stale detection: high-priority items with no recent update
    stale_critical = [
        i for i in p1_items + p2_items
        if _is_stale(i.get("updated_date"), today)
    ]

    # Recent activity: items updated within stale threshold
    recently_updated = [
        i for i in items
        if not _is_stale(i.get("updated_date"), today) and i.get("updated_date")
    ]

    # Top owners by open item load
    owner_load: dict[str, int] = {}
    for item in not_done:
        owner = item.get("owner") or "Unassigned"
        owner_load[owner] = owner_load.get(owner, 0) + 1

    completion_pct = round(len(done) / total * 100) if total > 0 else 0

    return {
        "total": total,
        "done": done,
        "active": active,
        "blocked": blocked,
        "open_": open_,
        "all_blocked": all_blocked,
        "not_done": not_done,
        "p1_items": p1_items,
        "p2_items": p2_items,
        "bugs": bugs,
        "milestone_items": milestone_items,
        "milestone_active": milestone_active,
        "milestone_done": milestone_done,
        "stale_critical": stale_critical,
        "recently_updated": recently_updated,
        "owner_load": owner_load,
        "completion_pct": completion_pct,
    }


# ---------------------------------------------------------------------------
# Category extractors
# ---------------------------------------------------------------------------


def _extract_progress(
    stats: dict[str, Any],
    doc: SourceDocument,
) -> list[ExtractedInsight]:
    """Produce up to 3 progress insights."""
    insights: list[ExtractedInsight] = []
    total = stats["total"]
    done = stats["done"]
    active = stats["active"]
    completion_pct = stats["completion_pct"]
    recently_updated = stats["recently_updated"]

    # Insight 1: Overall completion ratio (always emitted)
    done_ids = _ids(done)
    completion_conf = _completion_confidence(completion_pct)
    insights.append(
        _make_insight(
            category="progress",
            text=(
                f"{len(done)} of {total} work items completed "
                f"({completion_pct}% complete)."
            ),
            confidence=completion_conf,
            derivation_type="aggregated",
            source_pointer=_ptr(done_ids[:10]),
            doc=doc,
            metadata={"completion_pct": completion_pct, "total": total},
        )
    )

    # Insight 2: Active in-progress work (if meaningful)
    if active and len(insights) < _MAX_PER_CATEGORY:
        active_ids = _ids(active)
        insights.append(
            _make_insight(
                category="progress",
                text=f"{len(active)} item(s) are actively in progress.",
                confidence=0.80,
                derivation_type="aggregated",
                source_pointer=_ptr(active_ids[:10]),
                doc=doc,
                metadata={"active_count": len(active)},
            )
        )

    # Insight 3: Recent delivery activity — only when it adds signal beyond "in progress".
    # If recently_updated ≈ active_count the information is already captured above.
    # Emit only when there is material additional movement (non-active items being touched).
    extra_movement = len(recently_updated) - len(active)
    if extra_movement > 2 and len(insights) < _MAX_PER_CATEGORY:
        updated_ids = _ids(recently_updated)
        insights.append(
            _make_insight(
                category="progress",
                text=(
                    f"{len(recently_updated)} item(s) received updates in the last "
                    f"{_STALE_THRESHOLD_DAYS} days, indicating broad delivery movement "
                    f"across the backlog."
                ),
                confidence=0.72,
                derivation_type="aggregated",
                source_pointer=_ptr(updated_ids[:10]),
                doc=doc,
                metadata={"recently_updated_count": len(recently_updated)},
            )
        )

    return insights[:_MAX_PER_CATEGORY]


def _extract_blockers(
    stats: dict[str, Any],
    doc: SourceDocument,
) -> list[ExtractedInsight]:
    """Produce up to 3 blocker insights."""
    insights: list[ExtractedInsight] = []
    all_blocked = stats["all_blocked"]

    if not all_blocked:
        return insights

    # Insight 1: Total blocked count
    blocked_ids = _ids(all_blocked)
    titles_preview = _title_list(all_blocked, max_n=3)
    insights.append(
        _make_insight(
            category="blocker",
            text=(
                f"{len(all_blocked)} item(s) are blocked or on hold"
                f"{': ' + titles_preview if titles_preview else ''}."
            ),
            confidence=0.90,
            derivation_type="aggregated",
            source_pointer=_ptr(blocked_ids),
            doc=doc,
            metadata={"blocked_count": len(all_blocked)},
        )
    )

    # Insight 2: High-priority blockers (if any)
    high_pri_blocked = [
        i for i in all_blocked
        if i.get("priority") in (_CRITICAL_PRIORITY, _HIGH_PRIORITY)
    ]
    if high_pri_blocked and len(insights) < _MAX_PER_CATEGORY:
        hp_ids = _ids(high_pri_blocked)
        insights.append(
            _make_insight(
                category="blocker",
                text=(
                    f"{len(high_pri_blocked)} blocked item(s) are critical or high priority, "
                    f"representing active delivery risk."
                ),
                confidence=0.88,
                derivation_type="inferred",
                source_pointer=_ptr(hp_ids),
                doc=doc,
                metadata={"high_priority_blocked": len(high_pri_blocked)},
            )
        )

    # Insight 3: Stale blocked items (blocked and not recently updated)
    stale_blocked = [
        i for i in all_blocked
        if _is_stale(i.get("updated_date"), _today())
    ]
    if stale_blocked and len(insights) < _MAX_PER_CATEGORY:
        sb_ids = _ids(stale_blocked)
        insights.append(
            _make_insight(
                category="blocker",
                text=(
                    f"{len(stale_blocked)} blocked item(s) have not been updated in over "
                    f"{_STALE_THRESHOLD_DAYS} days and may require escalation."
                ),
                confidence=0.85,
                derivation_type="inferred",
                source_pointer=_ptr(sb_ids),
                doc=doc,
                metadata={"stale_blocked": len(stale_blocked)},
            )
        )

    return insights[:_MAX_PER_CATEGORY]


def _extract_risks(
    stats: dict[str, Any],
    doc: SourceDocument,
) -> list[ExtractedInsight]:
    """Produce up to 3 risk insights."""
    insights: list[ExtractedInsight] = []
    p1_items = stats["p1_items"]
    p2_items = stats["p2_items"]
    bugs = stats["bugs"]
    stale_critical = stats["stale_critical"]
    total = stats["total"]
    all_blocked = stats["all_blocked"]

    # Exclude items already surfaced in the blocker section to avoid double-counting.
    # Identity-based exclusion is safe here since all lists reference the same dicts.
    blocked_obj_ids = set(id(i) for i in all_blocked)
    p1_unblocked = [i for i in p1_items if id(i) not in blocked_obj_ids]
    p2_unblocked = [i for i in p2_items if id(i) not in blocked_obj_ids]

    # Insight 1: Critical/high-priority open concentration (excluding blockers)
    critical_open = p1_unblocked + p2_unblocked
    if critical_open:
        crit_ids = _ids(critical_open)
        p1_count = len(p1_unblocked)
        p2_count = len(p2_unblocked)
        pct = round(len(critical_open) / total * 100) if total > 0 else 0
        insights.append(
            _make_insight(
                category="risk",
                text=(
                    f"{len(critical_open)} open item(s) are critical or high priority "
                    f"({p1_count} critical, {p2_count} high), representing {pct}% of backlog."
                ),
                confidence=_risk_confidence(len(critical_open), total),
                derivation_type="aggregated",
                source_pointer=_ptr(crit_ids[:10]),
                doc=doc,
                metadata={"p1_count": p1_count, "p2_count": p2_count},
            )
        )

    # Insight 2: Stale critical work
    if stale_critical and len(insights) < _MAX_PER_CATEGORY:
        sc_ids = _ids(stale_critical)
        insights.append(
            _make_insight(
                category="risk",
                text=(
                    f"{len(stale_critical)} critical or high-priority item(s) have not been "
                    f"updated in over {_STALE_THRESHOLD_DAYS} days, indicating stalled "
                    f"high-risk work."
                ),
                confidence=0.83,
                derivation_type="inferred",
                source_pointer=_ptr(sc_ids),
                doc=doc,
                metadata={"stale_critical_count": len(stale_critical)},
            )
        )

    # Insight 3: Bug concentration
    if bugs and len(insights) < _MAX_PER_CATEGORY:
        bug_ids = _ids(bugs)
        bug_pct = round(len(bugs) / total * 100) if total > 0 else 0
        insights.append(
            _make_insight(
                category="risk",
                text=(
                    f"{len(bugs)} open bug(s) represent {bug_pct}% of active backlog — "
                    f"quality risk requires attention."
                ),
                confidence=0.78,
                derivation_type="aggregated",
                source_pointer=_ptr(bug_ids[:10]),
                doc=doc,
                metadata={"bug_count": len(bugs), "bug_pct": bug_pct},
            )
        )

    return insights[:_MAX_PER_CATEGORY]


def _extract_milestones(
    stats: dict[str, Any],
    doc: SourceDocument,
) -> list[ExtractedInsight]:
    """Produce up to 3 milestone insights."""
    insights: list[ExtractedInsight] = []
    milestone_active = stats["milestone_active"]
    milestone_done = stats["milestone_done"]
    milestone_items = stats["milestone_items"]

    if not milestone_items:
        return insights

    # Insight 1: Active epics / features
    if milestone_active:
        ma_ids = _ids(milestone_active)
        titles_preview = _title_list(milestone_active, max_n=3)
        insights.append(
            _make_insight(
                category="milestone",
                text=(
                    f"{len(milestone_active)} epic(s) or feature(s) are in progress"
                    f"{': ' + titles_preview if titles_preview else ''}."
                ),
                confidence=0.82,
                derivation_type="aggregated",
                source_pointer=_ptr(ma_ids),
                doc=doc,
                metadata={"milestone_active_count": len(milestone_active)},
            )
        )

    # Insight 2: Completed milestones
    if milestone_done and len(insights) < _MAX_PER_CATEGORY:
        md_ids = _ids(milestone_done)
        titles_preview = _title_list(milestone_done, max_n=3)
        insights.append(
            _make_insight(
                category="milestone",
                text=(
                    f"{len(milestone_done)} epic(s) or feature(s) completed this iteration"
                    f"{': ' + titles_preview if titles_preview else ''}."
                ),
                confidence=0.87,
                derivation_type="aggregated",
                source_pointer=_ptr(md_ids),
                doc=doc,
                metadata={"milestone_done_count": len(milestone_done)},
            )
        )

    # Insight 3: High-priority milestones not yet done
    high_pri_milestones = [
        i for i in milestone_active
        if i.get("priority") in (_CRITICAL_PRIORITY, _HIGH_PRIORITY)
    ]
    if high_pri_milestones and len(insights) < _MAX_PER_CATEGORY:
        hpm_ids = _ids(high_pri_milestones)
        insights.append(
            _make_insight(
                category="milestone",
                text=(
                    f"{len(high_pri_milestones)} high-priority epic(s) or feature(s) "
                    f"are incomplete and require leadership attention."
                ),
                confidence=0.80,
                derivation_type="inferred",
                source_pointer=_ptr(hpm_ids),
                doc=doc,
                metadata={"high_pri_milestone_count": len(high_pri_milestones)},
            )
        )

    return insights[:_MAX_PER_CATEGORY]


def _extract_priority(
    stats: dict[str, Any],
    doc: SourceDocument,
) -> list[ExtractedInsight]:
    """Produce up to 3 priority focus area insights."""
    insights: list[ExtractedInsight] = []
    p1_items = stats["p1_items"]
    not_done = stats["not_done"]
    owner_load = stats["owner_load"]

    # Insight 1: Priority-1 critical focus (if any)
    if p1_items:
        p1_ids = _ids(p1_items)
        titles_preview = _title_list(p1_items, max_n=3)
        insights.append(
            _make_insight(
                category="priority",
                text=(
                    f"{len(p1_items)} critical-priority item(s) demand immediate focus"
                    f"{': ' + titles_preview if titles_preview else ''}."
                ),
                confidence=0.88,
                derivation_type="aggregated",
                source_pointer=_ptr(p1_ids[:10]),
                doc=doc,
                metadata={"p1_count": len(p1_items)},
            )
        )

    # Insight 2: Open-backlog priority distribution — computed from not_done items only.
    # Framed as an executive signal, not a raw stats dump.
    if not_done and len(insights) < _MAX_PER_CATEGORY:
        open_priority_counts: dict[int, int] = {}
        for item in not_done:
            p = item.get("priority")
            if isinstance(p, int):
                open_priority_counts[p] = open_priority_counts.get(p, 0) + 1

        if open_priority_counts:
            dist_parts = [
                f"P{p}: {count}"
                for p, count in sorted(open_priority_counts.items())
            ]
            insights.append(
                _make_insight(
                    category="priority",
                    text=(
                        f"Open backlog of {len(not_done)} item(s) by priority — "
                        f"{', '.join(dist_parts)}."
                    ),
                    confidence=0.75,
                    derivation_type="aggregated",
                    source_pointer=None,
                    doc=doc,
                    metadata={"open_priority_distribution": open_priority_counts},
                )
            )

    # Insight 3: Concentration risk — one owner holds ≥30% of open work.
    # Threshold avoids noise on small boards or balanced teams.
    if len(owner_load) > 1 and not_done and len(insights) < _MAX_PER_CATEGORY:
        top_owner, top_count = max(owner_load.items(), key=lambda x: x[1])
        pct = round(top_count / len(not_done) * 100)
        if top_owner != "Unassigned" and pct >= 30:
            insights.append(
                _make_insight(
                    category="priority",
                    text=(
                        f"{top_owner} holds {top_count} open item(s) ({pct}% of active backlog) "
                        f"— concentration may indicate capacity risk."
                    ),
                    confidence=0.70,
                    derivation_type="inferred",
                    source_pointer=None,
                    doc=doc,
                    metadata={"top_owner": top_owner, "top_owner_count": top_count},
                )
            )

    return insights[:_MAX_PER_CATEGORY]


# ---------------------------------------------------------------------------
# Fallback for empty input
# ---------------------------------------------------------------------------


def _fallback_insights(doc: SourceDocument) -> list[ExtractedInsight]:
    """Return a minimal insight set when no work items are available."""
    return [
        _make_insight(
            category="progress",
            text=f"No work items provided for board: {doc.title}.",
            confidence=0.60,
            derivation_type="inferred",
            source_pointer=None,
            doc=doc,
            metadata={"fallback": True},
        )
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_state(state: str) -> str:
    """Return "done", "active", "blocked", or "open" for a state string."""
    s = state.lower().strip()
    if s in _DONE_STATES:
        return "done"
    if s in _ACTIVE_STATES:
        return "active"
    if s in _BLOCKED_STATES:
        return "blocked"
    return "open"


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _is_stale(updated_date_str: str | None, today: date) -> bool:
    """Return True if the item has not been updated within the stale threshold."""
    if not updated_date_str:
        return False
    try:
        updated = date.fromisoformat(str(updated_date_str)[:10])
        return (today - updated).days > _STALE_THRESHOLD_DAYS
    except (ValueError, TypeError):
        return False


def _ids(items: list[dict[str, Any]]) -> list[Any]:
    """Extract non-None IDs from a list of items."""
    return [i["id"] for i in items if i.get("id") is not None]


def _ptr(ids: list[Any]) -> str | None:
    """Build a source_pointer string from a list of item IDs."""
    if not ids:
        return None
    return "items:" + ",".join(str(i) for i in ids)


def _title_list(items: list[dict[str, Any]], max_n: int) -> str:
    """Build a concise title preview string from the first max_n items."""
    titles = [i["title"] for i in items[:max_n] if i.get("title")]
    if not titles:
        return ""
    result = ", ".join(f'"{t}"' for t in titles)
    if len(items) > max_n:
        result += f", +{len(items) - max_n} more"
    return result


def _completion_confidence(pct: int) -> float:
    """Derive confidence from completion percentage — high pct = clearer signal."""
    # Sigmoid-inspired: 0% or 100% both have moderate confidence; mid-range lower
    return round(0.70 + 0.15 * math.cos(math.pi * (pct - 50) / 100), 2)


def _risk_confidence(critical_count: int, total: int) -> float:
    """Higher ratio of critical items → higher risk confidence."""
    if total == 0:
        return 0.70
    ratio = critical_count / total
    return round(min(0.92, 0.70 + ratio * 0.40), 2)


def _make_insight(
    *,
    category: str,
    text: str,
    confidence: float,
    derivation_type: str,
    source_pointer: str | None,
    doc: SourceDocument,
    metadata: dict[str, Any],
) -> ExtractedInsight:
    return ExtractedInsight(
        category=category,
        text=text,
        confidence=round(max(0.40, min(0.95, confidence)), 2),
        source_type=doc.source_type,
        source_id=doc.source_id,
        source_pointer=source_pointer,
        derivation_type=derivation_type,
        metadata=metadata,
    )
