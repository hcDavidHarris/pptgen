"""Content Intelligence Layer — Phase 11C.

Prompt-driven content enrichment pipeline with deterministic fallback.
Sits between authoring input and the governance/resolution stages.

Phase 11C additions: semantic primitive system.

Pipeline stages (in order)::

    narrative_builder  → build_narrative()           ContentIntent → list[SlideIntent]
    primitive selector → select_primitive()          SlideIntent.primitive assigned
    content_expander   → expand_slide()              SlideIntent → EnrichedSlideContent
    insight_generator  → generate_insights()         EnrichedSlideContent → EnrichedSlideContent
    slide_critic       → critique_slide()            EnrichedSlideContent → EnrichedSlideContent
    primitive validator → validate_primitive_content() metadata annotated

Normalizer (pipeline bridge)::

    normalizer         → normalize_for_pipeline()    EnrichedSlideContent → dict

Orchestration::

    run_content_intelligence(content_intent) → list[EnrichedSlideContent]

Guardrails::

    validate_slide_intent(SlideIntent) → bool
    validate_enriched_content(EnrichedSlideContent) → bool
    validate_insight_output(EnrichedSlideContent) → bool

Primitive system (Phase 11C)::

    get_primitive(name) → SemanticPrimitiveDefinition
    list_primitive_names() → list[str]
    get_all_primitives() → list[SemanticPrimitiveDefinition]
    select_primitive(intent_type) → str
    validate_primitive_content(content, primitive_name) → PrimitiveValidationResult
    SemanticPrimitiveDefinition
    PrimitiveValidationResult
    FALLBACK_PRIMITIVE_NAME

Public API::

    from pptgen.content_intelligence import (
        ContentIntent,
        SlideIntent,
        EnrichedSlideContent,
        run_content_intelligence,
    )
"""

from .content_intelligence_pipeline import run_content_intelligence
from .content_models import ContentIntent, EnrichedSlideContent, SlideIntent
from .content_expander import expand_slide
from .guardrails import validate_enriched_content, validate_insight_output, validate_slide_intent
from .insight_generator import generate_insights
from .narrative_builder import build_narrative
from .normalizer import normalize_for_pipeline
from .primitive_models import SemanticPrimitiveDefinition
from .primitive_registry import (
    FALLBACK_PRIMITIVE_NAME,
    get_all_primitives,
    get_primitive,
    list_primitive_names,
)
from .primitive_selector import select_primitive
from .primitive_validator import PrimitiveValidationResult, validate_primitive_content
from .slide_critic import critique_slide

__all__ = [
    # Core models
    "ContentIntent",
    "SlideIntent",
    "EnrichedSlideContent",
    # Pipeline orchestration
    "run_content_intelligence",
    # Pipeline stages
    "build_narrative",
    "expand_slide",
    "generate_insights",
    "critique_slide",
    # Normalizer
    "normalize_for_pipeline",
    # Generic guardrails
    "validate_slide_intent",
    "validate_enriched_content",
    "validate_insight_output",
    # Primitive system (Phase 11C)
    "SemanticPrimitiveDefinition",
    "PrimitiveValidationResult",
    "get_primitive",
    "list_primitive_names",
    "get_all_primitives",
    "select_primitive",
    "validate_primitive_content",
    "FALLBACK_PRIMITIVE_NAME",
]
