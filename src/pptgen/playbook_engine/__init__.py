"""pptgen playbook execution engine — Phase 5A.

Public API::

    from pptgen.playbook_engine import execute_playbook, execute_playbook_full
    from pptgen.playbook_engine import PlaybookNotFoundError, get_default_template
    from pptgen.playbook_engine.execution_strategy import DETERMINISTIC, AI

    # Backward-compatible (returns PresentationSpec only)
    spec = execute_playbook("ado-summary-to-weekly-delivery", text)
    spec = execute_playbook("ado-summary-to-weekly-delivery", text, strategy="ai")

    # Extended (returns spec + optional fallback note)
    spec, notes = execute_playbook_full("ado-summary-to-weekly-delivery", text, strategy="ai")
"""

from .engine import execute_playbook, execute_playbook_full
from .playbook_loader import PlaybookNotFoundError
from .template_mapping import get_default_template

__all__ = [
    "execute_playbook",
    "execute_playbook_full",
    "PlaybookNotFoundError",
    "get_default_template",
]
