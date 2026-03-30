"""Semantic primitive registry — Phase 11C.

Single source of truth for all semantic slide primitives.

The registry contains 10 semantic primitives + 1 explicit fallback.
Each primitive is a content-quality contract that forces a specific
reasoning pattern.  Primitives encode *intent*, not layout.

Primitive set (focused, high-value):
    1.  problem_statement         — Surface a problem worth solving
    2.  why_it_matters            — Explain strategic significance
    3.  before_after_transformation — Contrast current vs. desired state
    4.  metrics_with_insight      — Measurable evidence + interpretation
    5.  capability_maturity       — Capability or readiness progression
    6.  architecture_explanation  — System / structural design explanation
    7.  recommendation            — Recommended action with rationale + outcome
    8.  decision_framework        — Structured criteria or options for a decision
    9.  roadmap                   — Sequenced plan with phases / milestones
    10. risk_and_mitigation       — Risks with corresponding responses
    F.  key_points_summary        — Explicit bounded fallback (not a generic dump)

Public API:
    get_primitive(name: str) -> SemanticPrimitiveDefinition
    list_primitive_names() -> list[str]
    get_all_primitives() -> list[SemanticPrimitiveDefinition]
    FALLBACK_PRIMITIVE_NAME: str
"""

from __future__ import annotations

from .primitive_models import SemanticPrimitiveDefinition

# ---------------------------------------------------------------------------
# Fallback constant — used by selector and validator
# ---------------------------------------------------------------------------

FALLBACK_PRIMITIVE_NAME: str = "key_points_summary"

# ---------------------------------------------------------------------------
# Primitive definitions
# ---------------------------------------------------------------------------

_PRIMITIVES: dict[str, SemanticPrimitiveDefinition] = {
    "problem_statement": SemanticPrimitiveDefinition(
        name="problem_statement",
        description=(
            "Surfaces a specific, evidenced problem that demands attention "
            "and states at least one consequence of inaction."
        ),
        minimum_supporting_points=3,
        requires_implications=True,
        minimum_implications=1,
        allowed_intent_types=("problem", "challenge", "gap", "pain"),
        normalization_hint="problem-assertion-with-evidence",
        validation_notes=(
            "assertion must be a non-empty problem claim",
            "at least 3 supporting points providing evidence",
            "at least 1 implication stating a consequence of inaction",
        ),
    ),

    "why_it_matters": SemanticPrimitiveDefinition(
        name="why_it_matters",
        description=(
            "Explains the strategic significance of a topic: "
            "the stakes, the 'so what', and why the audience should care."
        ),
        minimum_supporting_points=2,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("context", "background", "motivation", "why", "significance"),
        normalization_hint="significance-assertion-with-rationale",
        validation_notes=(
            "assertion must state why the topic matters",
            "at least 2 supporting points explaining the significance",
        ),
    ),

    "before_after_transformation": SemanticPrimitiveDefinition(
        name="before_after_transformation",
        description=(
            "Contrasts current state with the desired or post-change state, "
            "making the transformation concrete and tangible."
        ),
        minimum_supporting_points=4,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("transformation", "change", "transition", "evolution", "before_after"),
        normalization_hint="transformation-contrast-structure",
        validation_notes=(
            "assertion must name the transformation clearly",
            "at least 4 supporting points (2 describing before, 2 describing after)",
        ),
    ),

    "metrics_with_insight": SemanticPrimitiveDefinition(
        name="metrics_with_insight",
        description=(
            "Presents measurable evidence combined with interpretation: "
            "what the numbers say and what they mean."
        ),
        minimum_supporting_points=2,
        requires_implications=True,
        minimum_implications=1,
        allowed_intent_types=("metrics", "impact", "performance", "results", "data", "evidence"),
        normalization_hint="metrics-with-interpretation",
        validation_notes=(
            "assertion must make a measurable or evidence-backed claim",
            "at least 2 supporting points, at least 1 of which contains a metric or measurable claim",
            "at least 1 implication interpreting what the metrics mean",
        ),
    ),

    "capability_maturity": SemanticPrimitiveDefinition(
        name="capability_maturity",
        description=(
            "Describes a progression of capability, readiness, or organizational maturity "
            "across named levels or stages."
        ),
        minimum_supporting_points=2,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("maturity", "capability", "readiness", "assessment", "progression"),
        normalization_hint="maturity-level-progression",
        validation_notes=(
            "assertion must describe the capability or maturity being assessed",
            "at least 2 supporting points describing distinct stages or levels",
        ),
    ),

    "architecture_explanation": SemanticPrimitiveDefinition(
        name="architecture_explanation",
        description=(
            "Explains a system, technical structure, or design: "
            "what it is, how it works, and its key components or principles."
        ),
        minimum_supporting_points=3,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("architecture", "technical", "system", "design", "structure", "how_it_works"),
        normalization_hint="system-explanation-with-components",
        validation_notes=(
            "assertion must describe what the system or architecture does",
            "at least 3 supporting points covering components, layers, or design principles",
        ),
    ),

    "recommendation": SemanticPrimitiveDefinition(
        name="recommendation",
        description=(
            "States a recommended course of action, explains the rationale, "
            "and declares the expected outcome or benefit."
        ),
        minimum_supporting_points=2,
        requires_implications=True,
        minimum_implications=1,
        allowed_intent_types=("recommendation", "action", "next_steps", "solution", "directive"),
        normalization_hint="recommendation-with-rationale-and-outcome",
        validation_notes=(
            "assertion must state the recommendation clearly",
            "at least 2 supporting points providing rationale",
            "at least 1 implication stating the expected outcome or benefit",
        ),
    ),

    "decision_framework": SemanticPrimitiveDefinition(
        name="decision_framework",
        description=(
            "Structures how a decision should be made: "
            "the decision context, evaluation criteria, and available options."
        ),
        minimum_supporting_points=2,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("decision", "options", "tradeoffs", "criteria", "framework", "choice"),
        normalization_hint="decision-criteria-or-options",
        validation_notes=(
            "assertion must state the decision question or context",
            "at least 2 supporting points covering criteria, options, or tradeoffs",
        ),
    ),

    "roadmap": SemanticPrimitiveDefinition(
        name="roadmap",
        description=(
            "Describes a sequenced plan with named phases or milestones "
            "oriented toward a declared goal."
        ),
        minimum_supporting_points=2,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("roadmap", "plan", "timeline", "phases", "milestones", "sequence"),
        normalization_hint="phased-plan-with-goal",
        validation_notes=(
            "assertion must state the roadmap goal or objective",
            "at least 2 supporting points describing distinct phases or milestones",
        ),
    ),

    "risk_and_mitigation": SemanticPrimitiveDefinition(
        name="risk_and_mitigation",
        description=(
            "Identifies risks in a given context and pairs each risk "
            "with a corresponding mitigation strategy."
        ),
        minimum_supporting_points=2,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("risk", "mitigation", "concerns", "threats", "risk_management"),
        normalization_hint="risk-mitigation-pairs",
        validation_notes=(
            "assertion must frame the risk context",
            "at least 2 supporting points, each describing a risk or a mitigation",
        ),
    ),

    # Explicit bounded fallback — NOT a generic dump.
    # Used when no semantic primitive matches the intent type.
    FALLBACK_PRIMITIVE_NAME: SemanticPrimitiveDefinition(
        name=FALLBACK_PRIMITIVE_NAME,
        description=(
            "Bounded fallback primitive for slides that do not match a specific "
            "semantic pattern.  Still enforces minimum content depth."
        ),
        minimum_supporting_points=3,
        requires_implications=False,
        minimum_implications=0,
        allowed_intent_types=("summary", "overview", "introduction", "conclusion"),
        normalization_hint="key-points-summary",
        validation_notes=(
            "assertion must be a non-empty content claim",
            "at least 3 supporting points providing substantive content",
        ),
    ),
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_primitive(name: str) -> SemanticPrimitiveDefinition:
    """Return the SemanticPrimitiveDefinition for *name*.

    Args:
        name: Primitive name (e.g. ``"problem_statement"``).

    Returns:
        The matching SemanticPrimitiveDefinition.

    Raises:
        KeyError: If *name* is not registered.
    """
    return _PRIMITIVES[name]


def list_primitive_names() -> list[str]:
    """Return all registered primitive names in insertion order.

    Returns:
        list of primitive name strings.
    """
    return list(_PRIMITIVES.keys())


def get_all_primitives() -> list[SemanticPrimitiveDefinition]:
    """Return all registered primitives in insertion order.

    Returns:
        list of SemanticPrimitiveDefinition objects.
    """
    return list(_PRIMITIVES.values())
