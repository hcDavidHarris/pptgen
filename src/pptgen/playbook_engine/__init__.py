"""pptgen playbook execution engine — Phase 4 Stage 2.

Public API::

    from pptgen.playbook_engine import execute_playbook, PlaybookNotFoundError

    spec = execute_playbook("ado-summary-to-weekly-delivery", text)
"""

from .engine import execute_playbook
from .playbook_loader import PlaybookNotFoundError

__all__ = ["execute_playbook", "PlaybookNotFoundError"]
