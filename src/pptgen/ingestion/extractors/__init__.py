"""Ingestion extractors package.

Phase 12A:  stub extractors for all source types.
Phase 12B:  real extractor for zoom_transcript; stubs retained for ado_board/ado_repo.
"""

from .ado_board_extractor import extract as extract_ado_board
from .ado_repo_extractor import extract as extract_ado_repo
from .transcript_extractor import extract as extract_transcript
from .zoom_transcript_extractor import extract as extract_zoom_transcript

__all__ = [
    "extract_transcript",
    "extract_zoom_transcript",
    "extract_ado_board",
    "extract_ado_repo",
]
