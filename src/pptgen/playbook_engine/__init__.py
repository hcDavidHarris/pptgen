"""pptgen playbook execution engine — Phase 4 Stage 2.

Public API::

    from pptgen.playbook_engine import execute_playbook, PlaybookNotFoundError
    from pptgen.playbook_engine import get_default_template

    spec = execute_playbook("ado-summary-to-weekly-delivery", text)
    tid  = get_default_template("ado-summary-to-weekly-delivery")
"""

from .engine import execute_playbook
from .playbook_loader import PlaybookNotFoundError
from .template_mapping import get_default_template

__all__ = ["execute_playbook", "PlaybookNotFoundError", "get_default_template"]
