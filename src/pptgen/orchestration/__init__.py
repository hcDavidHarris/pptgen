"""pptgen orchestration layer — Phase 5E.

Provides batch generation over directories of input files.

Public API::

    from pptgen.orchestration import generate_batch, BatchResult, BatchItemResult
"""

from .batch_generator import BatchItemResult, BatchResult, generate_batch

__all__ = ["generate_batch", "BatchResult", "BatchItemResult"]
