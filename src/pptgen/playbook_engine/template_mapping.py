"""Default template mapping for playbook routes.

Maps each known playbook_id to its preferred template_id.  The mapping is
used when no explicit ``--template`` override is provided by the caller.

Precedence rule (enforced by the pipeline):

    1. explicit template_id override (CLI ``--template``)
    2. playbook-specific default from this mapping
    3. PresentationSpec default field (``"ops_review_v1"``)

All template IDs in this mapping must exist in ``templates/registry.yaml``.
If a new playbook is added, a corresponding entry should be added here.
"""

from __future__ import annotations


#: Maps playbook_id → preferred template_id.
#: architecture-notes-to-adr-deck defaults to a template that emphasises
#: diagram and decision-record layouts; all others use the general ops template.
_DEFAULT_TEMPLATE_MAP: dict[str, str] = {
    "meeting-notes-to-eos-rocks": "ops_review_v1",
    "ado-summary-to-weekly-delivery": "ops_review_v1",
    "architecture-notes-to-adr-deck": "architecture_overview_v1",
    "devops-metrics-to-scorecard": "ops_review_v1",
    "generic-summary-playbook": "ops_review_v1",
}

#: Returned when the playbook_id is not in the map.
_FALLBACK_TEMPLATE = "ops_review_v1"


def get_default_template(playbook_id: str) -> str:
    """Return the default template ID for *playbook_id*.

    Args:
        playbook_id: A playbook identifier (e.g. ``"meeting-notes-to-eos-rocks"``).

    Returns:
        A registered template ID string.  Falls back to ``"ops_review_v1"``
        for any playbook_id not in the mapping.
    """
    return _DEFAULT_TEMPLATE_MAP.get(playbook_id, _FALLBACK_TEMPLATE)
