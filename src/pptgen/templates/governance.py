"""Template governance — Phase 8 Stage 3.

Provides:
- :class:`GovernanceStore` — SQLite-backed runtime governance state (default
  versions, deprecation, lifecycle overrides, audit trail).
- Validation helpers that enforce governance rules before governance mutations
  and before template resolution.
- Helper functions that merge manifest state with governance state.

Design principle
----------------
The :class:`~pptgen.templates.registry.VersionedTemplateRegistry` is immutable
(loaded from the YAML manifest and never mutated).  :class:`GovernanceStore`
holds the *runtime* governance layer that overlays it:

- which version is the production default
- which versions are deprecated
- lifecycle overrides (e.g. to deprecate a template without editing the repo)

Resolution code calls :func:`get_effective_lifecycle` and
:func:`get_effective_default_version` to apply both layers.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Template, TemplateVersion
from .registry import VersionedTemplateRegistry


# ---------------------------------------------------------------------------
# Lifecycle rules
# ---------------------------------------------------------------------------

_LIFECYCLE_STATES = frozenset({"draft", "review", "approved", "deprecated"})

_NEW_RUN_ALLOWED: dict[str, bool] = {
    "draft":      False,
    "review":     False,   # admin override handled at API layer if desired
    "approved":   True,
    "deprecated": False,
}

_REPLAY_ALLOWED: dict[str, bool] = {
    "draft":      True,
    "review":     True,
    "approved":   True,
    "deprecated": True,
}


def is_new_run_allowed(lifecycle_status: str) -> bool:
    """Return True when *lifecycle_status* permits starting a new run."""
    return _NEW_RUN_ALLOWED.get(lifecycle_status, False)


def is_replay_allowed(lifecycle_status: str) -> bool:
    """Return True when *lifecycle_status* permits replay (retry/rerun)."""
    return _REPLAY_ALLOWED.get(lifecycle_status, True)


def validate_lifecycle_transition(current: str, proposed: str) -> None:
    """Raise :exc:`ValueError` for invalid lifecycle state values.

    Any known-state → any known-state transition is permitted at Stage 3.
    This can be tightened in a future stage (e.g. approved → deprecated only).
    """
    if proposed not in _LIFECYCLE_STATES:
        raise ValueError(
            f"Invalid lifecycle_status '{proposed}'. "
            f"Must be one of: {sorted(_LIFECYCLE_STATES)}"
        )


# ---------------------------------------------------------------------------
# Governance validation helpers
# ---------------------------------------------------------------------------

def validate_version_promotable(
    registry: VersionedTemplateRegistry,
    governance: "GovernanceStore",
    template_id: str,
    version: str,
) -> None:
    """Raise :exc:`ValueError` if *version* cannot be promoted to default."""
    template = registry.get_template(template_id)
    if template is None:
        raise ValueError(f"Template not found: {template_id}")
    ver = registry.get_template_version(template_id, version)
    if ver is None:
        raise ValueError(f"Version not found: {template_id}@{version}")
    if governance.is_deprecated(template_id, version):
        raise ValueError(
            f"Cannot promote deprecated version {version}. "
            "Undeprecate it first."
        )


def validate_version_deprecatable(
    registry: VersionedTemplateRegistry,
    governance: "GovernanceStore",
    template_id: str,
    version: str,
) -> None:
    """Raise :exc:`ValueError` if *version* cannot be deprecated."""
    template = registry.get_template(template_id)
    if template is None:
        raise ValueError(f"Template not found: {template_id}")
    ver = registry.get_template_version(template_id, version)
    if ver is None:
        raise ValueError(f"Version not found: {template_id}@{version}")
    if governance.is_deprecated(template_id, version):
        raise ValueError(f"Version {version} is already deprecated.")
    # Cannot deprecate the only non-deprecated version if it's the default
    all_versions = registry.get_template_versions(template_id)
    non_deprecated = [
        v for v in all_versions
        if not governance.is_deprecated(template_id, v.version)
    ]
    if len(non_deprecated) == 1 and non_deprecated[0].version == version:
        raise ValueError(
            f"Cannot deprecate the only non-deprecated version ({version})."
        )


# ---------------------------------------------------------------------------
# Effective-state helpers
# ---------------------------------------------------------------------------

def get_effective_lifecycle(
    registry: VersionedTemplateRegistry,
    governance: "GovernanceStore",
    template_id: str,
) -> str:
    """Return the effective lifecycle: governance override if present, else manifest."""
    override = governance.get_lifecycle(template_id)
    if override is not None:
        return override
    template = registry.get_template(template_id)
    return template.lifecycle_status if template else "draft"


def get_effective_default_version(
    registry: VersionedTemplateRegistry,
    governance: "GovernanceStore",
    template_id: str,
) -> Optional[TemplateVersion]:
    """Return the default version: governance-pinned if set, else highest semver approved.

    Never returns a deprecated version as the default, even if explicitly pinned.
    """
    pinned = governance.get_default_version(template_id)
    if pinned:
        ver = registry.get_template_version(template_id, pinned)
        if ver and not governance.is_deprecated(template_id, pinned):
            return ver
        # pinned version was deprecated or removed — fall through to semver resolution

    # Fall back to highest semver among non-deprecated versions
    lifecycle = get_effective_lifecycle(registry, governance, template_id)
    if lifecycle not in ("approved", "review"):
        return None

    from .registry import _parse_semver
    all_versions = registry.get_template_versions(template_id)  # sorted ascending
    candidates = [
        v for v in all_versions
        if not governance.is_deprecated(template_id, v.version)
    ]
    return candidates[-1] if candidates else None


def apply_governance_to_version(
    version: TemplateVersion,
    governance: "GovernanceStore",
    default_version_str: Optional[str],
) -> TemplateVersion:
    """Return a copy of *version* with governance state fields populated."""
    dep = governance.get_deprecation(version.template_id, version.version)
    promo_ts = governance.get_promotion_timestamp(version.template_id, version.version)
    from dataclasses import replace
    return replace(
        version,
        is_default=(version.version == default_version_str),
        deprecated_at=dep["deprecated_at"] if dep else None,
        deprecation_reason=dep["reason"] if dep else None,
        promotion_timestamp=promo_ts,
    )


# ---------------------------------------------------------------------------
# GovernanceStore
# ---------------------------------------------------------------------------

_CREATE_TEMPLATE_GOV = """
CREATE TABLE IF NOT EXISTS template_governance (
    template_id     TEXT PRIMARY KEY,
    lifecycle_status TEXT NOT NULL,
    updated_at      TEXT NOT NULL
)
"""

_CREATE_VERSION_GOV = """
CREATE TABLE IF NOT EXISTS template_version_governance (
    template_id         TEXT NOT NULL,
    version             TEXT NOT NULL,
    is_default          INTEGER NOT NULL DEFAULT 0,
    deprecated_at       TEXT,
    deprecation_reason  TEXT,
    promotion_timestamp TEXT,
    PRIMARY KEY (template_id, version)
)
"""

_CREATE_AUDIT = """
CREATE TABLE IF NOT EXISTS governance_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,
    template_id     TEXT NOT NULL,
    template_version TEXT,
    actor           TEXT,
    reason          TEXT,
    timestamp       TEXT NOT NULL,
    metadata        TEXT
)
"""


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _parse_dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


class GovernanceStore:
    """SQLite-backed runtime governance state for the template registry.

    All mutation methods are thread-safe via an internal ``threading.Lock``.

    Governance state is *additive* on top of the manifest:
    - Lifecycle overrides take precedence over the manifest's lifecycle_status.
    - A pinned default version overrides semver-based default resolution.
    - Deprecation marks specific versions unavailable for new runs.
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_CREATE_TEMPLATE_GOV)
        self._conn.execute(_CREATE_VERSION_GOV)
        self._conn.execute(_CREATE_AUDIT)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Default version
    # ------------------------------------------------------------------

    def set_default_version(
        self,
        template_id: str,
        version: str,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> str | None:
        """Pin *version* as the default for *template_id*.

        Clears the previous default.  Returns the previous default version
        string, or ``None`` if there was none.
        """
        now = _now_iso()
        with self._lock:
            prev_row = self._conn.execute(
                "SELECT version FROM template_version_governance WHERE template_id = ? AND is_default = 1",
                (template_id,),
            ).fetchone()
            previous = prev_row["version"] if prev_row else None

            # Clear existing default
            self._conn.execute(
                "UPDATE template_version_governance SET is_default = 0 WHERE template_id = ?",
                (template_id,),
            )
            # Upsert new default
            self._conn.execute(
                """INSERT INTO template_version_governance
                       (template_id, version, is_default, promotion_timestamp)
                   VALUES (?, ?, 1, ?)
                   ON CONFLICT (template_id, version)
                   DO UPDATE SET is_default = 1, promotion_timestamp = ?""",
                (template_id, version, now, now),
            )
            self._conn.commit()
        return previous

    def get_default_version(self, template_id: str) -> Optional[str]:
        """Return the pinned default version string, or ``None``."""
        row = self._conn.execute(
            "SELECT version FROM template_version_governance WHERE template_id = ? AND is_default = 1",
            (template_id,),
        ).fetchone()
        return row["version"] if row else None

    def get_promotion_timestamp(
        self, template_id: str, version: str
    ) -> Optional[datetime]:
        """Return when *version* was last promoted, or ``None``."""
        row = self._conn.execute(
            "SELECT promotion_timestamp FROM template_version_governance WHERE template_id = ? AND version = ?",
            (template_id, version),
        ).fetchone()
        if row is None:
            return None
        return _parse_dt(row["promotion_timestamp"])

    # ------------------------------------------------------------------
    # Deprecation
    # ------------------------------------------------------------------

    def deprecate_version(
        self,
        template_id: str,
        version: str,
        reason: str,
        deprecated_at: Optional[datetime] = None,
        actor: Optional[str] = None,
    ) -> None:
        """Mark *version* as deprecated."""
        ts = (deprecated_at or datetime.now(tz=timezone.utc)).isoformat()
        with self._lock:
            self._conn.execute(
                """INSERT INTO template_version_governance
                       (template_id, version, is_default, deprecated_at, deprecation_reason)
                   VALUES (?, ?, 0, ?, ?)
                   ON CONFLICT (template_id, version)
                   DO UPDATE SET deprecated_at = ?, deprecation_reason = ?""",
                (template_id, version, ts, reason, ts, reason),
            )
            self._conn.commit()

    def undeprecate_version(self, template_id: str, version: str) -> None:
        """Remove deprecation from *version*."""
        with self._lock:
            self._conn.execute(
                """UPDATE template_version_governance
                   SET deprecated_at = NULL, deprecation_reason = NULL
                   WHERE template_id = ? AND version = ?""",
                (template_id, version),
            )
            self._conn.commit()

    def is_deprecated(self, template_id: str, version: str) -> bool:
        """Return ``True`` if *version* is marked deprecated."""
        row = self._conn.execute(
            "SELECT deprecated_at FROM template_version_governance WHERE template_id = ? AND version = ?",
            (template_id, version),
        ).fetchone()
        return row is not None and row["deprecated_at"] is not None

    def get_deprecation(
        self, template_id: str, version: str
    ) -> Optional[dict]:
        """Return ``{"deprecated_at": datetime, "reason": str}`` or ``None``."""
        row = self._conn.execute(
            "SELECT deprecated_at, deprecation_reason FROM template_version_governance "
            "WHERE template_id = ? AND version = ?",
            (template_id, version),
        ).fetchone()
        if row is None or row["deprecated_at"] is None:
            return None
        return {
            "deprecated_at": _parse_dt(row["deprecated_at"]),
            "reason": row["deprecation_reason"],
        }

    def get_deprecated_versions(self, template_id: str) -> list[str]:
        """Return list of deprecated version strings for *template_id*."""
        rows = self._conn.execute(
            "SELECT version FROM template_version_governance "
            "WHERE template_id = ? AND deprecated_at IS NOT NULL",
            (template_id,),
        ).fetchall()
        return [r["version"] for r in rows]

    # ------------------------------------------------------------------
    # Lifecycle overrides
    # ------------------------------------------------------------------

    def set_lifecycle(
        self,
        template_id: str,
        lifecycle_status: str,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Override *template_id*'s lifecycle status at runtime."""
        now = _now_iso()
        with self._lock:
            self._conn.execute(
                """INSERT INTO template_governance (template_id, lifecycle_status, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT (template_id)
                   DO UPDATE SET lifecycle_status = ?, updated_at = ?""",
                (template_id, lifecycle_status, now, lifecycle_status, now),
            )
            self._conn.commit()

    def get_lifecycle(self, template_id: str) -> Optional[str]:
        """Return the governance lifecycle override, or ``None`` if none set."""
        row = self._conn.execute(
            "SELECT lifecycle_status FROM template_governance WHERE template_id = ?",
            (template_id,),
        ).fetchone()
        return row["lifecycle_status"] if row else None

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def add_audit_event(
        self,
        event_type: str,
        template_id: str,
        template_version: Optional[str] = None,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        **metadata,
    ) -> None:
        """Append an immutable audit event."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO governance_audit
                       (event_type, template_id, template_version, actor, reason,
                        timestamp, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_type,
                    template_id,
                    template_version,
                    actor,
                    reason,
                    _now_iso(),
                    json.dumps(metadata, default=str) if metadata else None,
                ),
            )
            self._conn.commit()

    def list_audit_events(
        self,
        template_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return audit events, newest first, optionally filtered by template."""
        if template_id:
            rows = self._conn.execute(
                "SELECT * FROM governance_audit WHERE template_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (template_id, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM governance_audit ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "event_type": r["event_type"],
                "template_id": r["template_id"],
                "template_version": r["template_version"],
                "actor": r["actor"],
                "reason": r["reason"],
                "timestamp": r["timestamp"],
                "metadata": json.loads(r["metadata"]) if r["metadata"] else None,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @classmethod
    def from_settings(cls, settings) -> "GovernanceStore":
        """Create a store using the same db file as the artifact/run stores."""
        return cls(db_path=settings.artifact_db_file)
