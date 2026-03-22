"""pptgen generation pipeline — Phase 4 orchestration layer.

Public API::

    from pptgen.pipeline import generate_presentation, PipelineError, PipelineResult

    result = generate_presentation(text)
    # result.stage       == "routed"
    # result.playbook_id == "meeting-notes-to-eos-rocks"
"""

from .generation_pipeline import PipelineError, PipelineResult, generate_presentation

__all__ = ["generate_presentation", "PipelineError", "PipelineResult"]
