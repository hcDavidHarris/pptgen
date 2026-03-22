"""Heuristic input classifier.

Assigns a score to each known playbook route based on keyword signals
found in the input text.  Returns the single highest-scoring playbook
identifier.  Tie-breaking uses a fixed priority order for determinism.

Design notes
------------
- Signals are checked as substring matches on lowercased input — no regex,
  no external dependencies, no ML models.
- The signal map is hardcoded here (not loaded from the routing table) so
  that classification is fast, self-contained, and testable in isolation.
- The routing table loader is a separate concern: it provides playbook
  metadata for Stage 2 execution and is not called during classification.
- ``generic-summary-playbook`` is the fallback; it is never assigned a
  score and is only returned when all other routes score zero.
"""

from __future__ import annotations


#: Fallback identifier returned when no route scores any signal match.
FALLBACK_PLAYBOOK = "generic-summary-playbook"

#: Tie-break priority order (index 0 = highest priority).
#: When two routes achieve the same score, the earlier one in this tuple wins.
_PRIORITY: tuple[str, ...] = (
    "architecture-notes-to-adr-deck",
    "ado-summary-to-weekly-delivery",
    "devops-metrics-to-scorecard",
    "meeting-notes-to-eos-rocks",
    FALLBACK_PLAYBOOK,
)

#: Keyword / phrase signals for each classifiable route.
#: Each signal is matched as a case-insensitive substring of the input.
#: Phrases are preferred over single words where possible to reduce noise.
_SIGNALS: dict[str, tuple[str, ...]] = {
    "architecture-notes-to-adr-deck": (
        "architecture",
        "adr",
        "decision record",
        "architectural decision",
        "tradeoff",
        "trade-off",
        "option a",
        "option b",
        "constraints",
        "system context",
        "component",
        "interface",
        "dependency",
        "design decision",
        "design review",
        "system design",
    ),
    "ado-summary-to-weekly-delivery": (
        "sprint",
        "backlog",
        "velocity",
        "story points",
        "story point",
        "blocked",
        "azure devops",
        "ado",
        "epic",
        "work item",
        "work items",
        "pull request",
        "iteration",
        "release branch",
        "bug",
        "feature branch",
    ),
    "devops-metrics-to-scorecard": (
        "dora",
        "deployment frequency",
        "lead time for changes",
        "mttr",
        "change failure rate",
        "mean time to restore",
        "four key metrics",
        "ci/cd metrics",
        "deployment pipeline",
        "stability metric",
        "throughput metric",
    ),
    "meeting-notes-to-eos-rocks": (
        "meeting",
        "attendees",
        "agenda",
        "action items",
        "action item",
        "follow-up",
        "follow up",
        "decisions",
        "discussion",
        "attendee",
        "meeting notes",
        "minutes",
        "facilitator",
    ),
}


def classify(text: str) -> str:
    """Classify *text* and return a playbook identifier.

    Scores each route by counting how many of its signals appear in *text*
    (lowercased).  Returns the route with the highest score, using
    :data:`_PRIORITY` to break ties deterministically.

    Args:
        text: Normalised (lowercased, stripped) input text.

    Returns:
        A playbook identifier string.  Always returns exactly one value;
        never raises for any string input, including empty strings.
    """
    scores: dict[str, int] = {route: 0 for route in _SIGNALS}

    for route, signals in _SIGNALS.items():
        for signal in signals:
            if signal in text:
                scores[route] += 1

    best_score = max(scores.values())
    if best_score == 0:
        return FALLBACK_PLAYBOOK

    # Collect all routes that achieved the best score, then pick the
    # highest-priority one from _PRIORITY for deterministic tie-breaking.
    winners = {route for route, score in scores.items() if score == best_score}
    for route in _PRIORITY:
        if route in winners:
            return route

    return FALLBACK_PLAYBOOK  # unreachable; satisfies type checker
