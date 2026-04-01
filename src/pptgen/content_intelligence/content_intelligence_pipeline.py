"""Content Intelligence pipeline orchestrator — Phase 11A / 11C.

Coordinates the content intelligence stages into a single callable.
Each stage accepts and returns structured types — independently testable.

Phase 11C additions:
    1. Primitive selection — after narrative_builder, each SlideIntent receives
       a semantic primitive assignment via primitive_selector.select_primitive().
    2. Primitive-aware validation — after slide_critic, each EnrichedSlideContent
       is validated against its primitive's content-depth rules.  Results are
       recorded in metadata and do NOT abort the pipeline.

Pipeline stages:
    1. narrative_builder    ContentIntent → list[SlideIntent]
    2. primitive selection  SlideIntent.primitive assigned (Phase 11C)
    3. content_expander     SlideIntent → EnrichedSlideContent
    4. insight_generator    EnrichedSlideContent → EnrichedSlideContent
    5. slide_critic         EnrichedSlideContent → EnrichedSlideContent
    6. primitive validation metadata annotated with validation result (Phase 11C)
"""

from __future__ import annotations

from dataclasses import replace as _dc_replace

from .content_models import ContentIntent, EnrichedSlideContent
from .content_expander import expand_slide
from .insight_generator import generate_insights
from .narrative_builder import build_narrative
from .primitive_selector import select_primitive
from .primitive_validator import validate_primitive_content
from .slide_critic import critique_slide


def run_content_intelligence(
    content_intent: ContentIntent,
) -> list[EnrichedSlideContent]:
    """Orchestrate the full content intelligence pipeline.

    Stages:
        1. narrative_builder  — ContentIntent → list[SlideIntent]
        2. primitive selection — assigns semantic primitive to each SlideIntent
        3. content_expander   — SlideIntent   → EnrichedSlideContent
        4. insight_generator  — EnrichedSlideContent → EnrichedSlideContent
        5. slide_critic       — EnrichedSlideContent → EnrichedSlideContent
        6. primitive validation — annotates metadata; does NOT abort pipeline

    Each stage is pure and deterministic.  No LLM or external I/O.
    The normalizer (normalize_for_pipeline) is available separately for
    callers that need a pipeline-compatible dict representation.

    Args:
        content_intent: Authoring intent describing the topic and context.

    Returns:
        list[EnrichedSlideContent] — one item per slide, order preserved.
        Each item has a ``primitive`` field and
        ``metadata["primitive_validation"]`` recording the validation outcome.
    """
    # Stage 1: narrative
    slide_intents = build_narrative(content_intent)

    # Stage 2: primitive selection — assign semantic primitive to each intent
    slide_intents = [
        _dc_replace(si, primitive=select_primitive(si.intent_type))
        for si in slide_intents
    ]

    enriched_slides: list[EnrichedSlideContent] = []
    for slide_intent in slide_intents:
        # Stage 3: expansion
        enriched = expand_slide(slide_intent)
        # Stage 4: insights
        enriched = generate_insights(enriched)
        # Stage 5: critic
        enriched = critique_slide(enriched)

        # Stage 6: primitive-aware validation — non-blocking, metadata only
        primitive_name = enriched.primitive or slide_intent.primitive
        if primitive_name:
            validation_result = validate_primitive_content(enriched, primitive_name)
            updated_metadata = dict(enriched.metadata)
            updated_metadata["primitive_validation"] = {
                "passed": validation_result.passed,
                "primitive": validation_result.primitive_name,
                "violations": list(validation_result.violations),
            }
            enriched = _dc_replace(enriched, metadata=updated_metadata)

        enriched_slides.append(enriched)

    return enriched_slides
