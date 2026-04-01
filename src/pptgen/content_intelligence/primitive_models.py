"""Semantic primitive models — Phase 11C.

Defines the contract model for semantic slide primitives.

A SemanticPrimitiveDefinition encodes *intent*, not layout.  It tells the
content intelligence layer what reasoning pattern a slide must exhibit,
what fields are required, and what the minimum content depth looks like.

Design principles:
- Declarative: definitions are data, not code.
- Frozen: definitions cannot be mutated at runtime.
- Testable: every rule is explicit and checkable.
- Small: one model, one purpose.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticPrimitiveDefinition:
    """Immutable contract for a semantic slide primitive.

    Attributes:
        name: Unique identifier for this primitive (e.g. "problem_statement").
        description: One-sentence description of the primitive's purpose.
        minimum_supporting_points: Minimum number of supporting_points required.
        requires_implications: Whether at least one implication is mandatory.
        minimum_implications: Minimum number of implications when required (ignored
            when requires_implications is False).
        allowed_intent_types: Intent type strings that map to this primitive.
            Used by the primitive selector for deterministic routing.
        normalization_hint: Short descriptor that downstream observability tooling
            can use to annotate normalized output.  Not used by the renderer.
        validation_notes: Human-readable descriptions of the validation rules.
            Surfaced in violation messages and documentation.
    """

    name: str
    description: str
    minimum_supporting_points: int
    requires_implications: bool
    minimum_implications: int
    allowed_intent_types: tuple[str, ...]
    normalization_hint: str
    validation_notes: tuple[str, ...]
