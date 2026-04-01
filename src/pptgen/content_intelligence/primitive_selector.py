"""Primitive selector — Phase 11C.

Maps SlideIntent.intent_type to a semantic primitive name.

Design:
- Explicit: every mapping is declared, nothing is inferred dynamically.
- Deterministic: same intent_type always returns the same primitive name.
- Bounded fallback: unmatched intent types route to FALLBACK_PRIMITIVE_NAME,
  never to an unbounded generic.
- No silent failures: callers always receive a named primitive.

Public API:
    select_primitive(intent_type: str) -> str
    FALLBACK_PRIMITIVE_NAME  (re-exported for caller convenience)
"""

from __future__ import annotations

from .primitive_registry import FALLBACK_PRIMITIVE_NAME

# ---------------------------------------------------------------------------
# Explicit intent-type → primitive name mapping
# ---------------------------------------------------------------------------
# Each key is an intent_type string produced by narrative_builder.
# Keys are lowercased; select_primitive() normalises input before lookup.

_INTENT_TO_PRIMITIVE: dict[str, str] = {
    # problem_statement
    "problem": "problem_statement",
    "challenge": "problem_statement",
    "gap": "problem_statement",
    "pain": "problem_statement",

    # why_it_matters
    "context": "why_it_matters",
    "background": "why_it_matters",
    "motivation": "why_it_matters",
    "why": "why_it_matters",
    "significance": "why_it_matters",

    # before_after_transformation
    "transformation": "before_after_transformation",
    "change": "before_after_transformation",
    "transition": "before_after_transformation",
    "evolution": "before_after_transformation",
    "before_after": "before_after_transformation",

    # metrics_with_insight
    "metrics": "metrics_with_insight",
    "impact": "metrics_with_insight",
    "performance": "metrics_with_insight",
    "results": "metrics_with_insight",
    "data": "metrics_with_insight",
    "evidence": "metrics_with_insight",

    # capability_maturity
    "maturity": "capability_maturity",
    "capability": "capability_maturity",
    "readiness": "capability_maturity",
    "assessment": "capability_maturity",
    "progression": "capability_maturity",

    # architecture_explanation
    "architecture": "architecture_explanation",
    "technical": "architecture_explanation",
    "system": "architecture_explanation",
    "design": "architecture_explanation",
    "structure": "architecture_explanation",
    "how_it_works": "architecture_explanation",

    # recommendation
    "recommendation": "recommendation",
    "action": "recommendation",
    "next_steps": "recommendation",
    "solution": "recommendation",
    "directive": "recommendation",

    # decision_framework
    "decision": "decision_framework",
    "options": "decision_framework",
    "tradeoffs": "decision_framework",
    "criteria": "decision_framework",
    "framework": "decision_framework",
    "choice": "decision_framework",

    # roadmap
    "roadmap": "roadmap",
    "plan": "roadmap",
    "timeline": "roadmap",
    "phases": "roadmap",
    "milestones": "roadmap",
    "sequence": "roadmap",

    # risk_and_mitigation
    "risk": "risk_and_mitigation",
    "mitigation": "risk_and_mitigation",
    "concerns": "risk_and_mitigation",
    "threats": "risk_and_mitigation",
    "risk_management": "risk_and_mitigation",

    # key_points_summary (fallback, also explicit for known summary types)
    "summary": FALLBACK_PRIMITIVE_NAME,
    "overview": FALLBACK_PRIMITIVE_NAME,
    "introduction": FALLBACK_PRIMITIVE_NAME,
    "conclusion": FALLBACK_PRIMITIVE_NAME,
}


def select_primitive(intent_type: str) -> str:
    """Return the semantic primitive name for *intent_type*.

    Normalises *intent_type* to lowercase before lookup.  Unknown intent
    types route to ``FALLBACK_PRIMITIVE_NAME`` — never silently dropped.

    Args:
        intent_type: The intent type string from a SlideIntent.

    Returns:
        A registered primitive name string.  Always returns a value.
    """
    if not intent_type or not intent_type.strip():
        return FALLBACK_PRIMITIVE_NAME
    return _INTENT_TO_PRIMITIVE.get(intent_type.strip().lower(), FALLBACK_PRIMITIVE_NAME)
