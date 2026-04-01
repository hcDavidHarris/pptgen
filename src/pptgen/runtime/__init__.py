"""Runtime support package — per-run metadata, workspace management, and startup validation.

Public API::

    from pptgen.runtime import RunContext, StageTimer
    from pptgen.runtime import Workspace, WorkspaceManager
    from pptgen.runtime.startup import validate_startup, assert_startup_healthy
"""

from .run_context import RunContext, StageTimer
from .workspace import Workspace, WorkspaceManager

__all__ = ["RunContext", "StageTimer", "Workspace", "WorkspaceManager"]
