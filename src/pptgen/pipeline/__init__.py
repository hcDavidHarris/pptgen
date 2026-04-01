"""pptgen generation pipeline — Phase 4 orchestration layer.

Public API::

    from pptgen.pipeline import generate_presentation, PipelineError, PipelineResult

    result = generate_presentation(text)
    # result.stage             == "deck_planned"
    # result.playbook_id       == "meeting-notes-to-eos-rocks"
    # result.presentation_spec  is a PresentationSpec instance
    # result.slide_plan         is a SlidePlan instance
    # result.deck_definition    is a dict (pptgen deck YAML structure)
"""

from .generation_pipeline import PipelineError, PipelineResult, generate_presentation

__all__ = ["generate_presentation", "PipelineError", "PipelineResult"]
