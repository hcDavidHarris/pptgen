"""pptgen input router — Phase 4 Stage 1.

Classifies raw text input and returns a single playbook identifier.

Public API::

    from pptgen.input_router import route_input

    playbook_id = route_input(text)

For routing table metadata (playbook paths, example patterns, follow-up
steps), use the loader directly::

    from pptgen.input_router.routing_table_loader import load_routing_table

    entries = load_routing_table()
"""

from .router import InputRouterError, route_input

__all__ = ["route_input", "InputRouterError"]
