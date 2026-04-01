"""Per-run metadata model for the pptgen platform.

:class:`RunContext` is a lightweight dataclass that travels with a pipeline
execution.  It captures the run identifier, request linkage, stage timings,
workspace location, and settings fingerprint required for observability,
debugging, and reproducibility.

Usage::

    from pptgen.runtime import RunContext

    ctx = RunContext(
        request_id="abc123",
        profile="prod",
        mode="deterministic",
        config_fingerprint=get_settings().fingerprint,
    )

    ctx.start_stage("route_input")
    playbook_id = route_input(text)
    ctx.end_stage("route_input")
    ctx.playbook_id = playbook_id

    result = generate_presentation(text, run_context=ctx)
    print(ctx.as_dict())
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class StageTimer:
    """Timing record for a single pipeline stage.

    Attributes:
        stage:      Stage name (e.g. ``"route_input"``, ``"render"``).
        started_at: :func:`time.monotonic` value at stage start.
        ended_at:   :func:`time.monotonic` value at stage end, or ``None``
                    if the stage has not yet completed.
    """

    stage: str
    started_at: float           # time.monotonic()
    ended_at: float | None = None

    @property
    def duration_ms(self) -> float | None:
        """Elapsed milliseconds, or ``None`` if the stage is still running."""
        if self.ended_at is None:
            return None
        return (self.ended_at - self.started_at) * 1000


@dataclass
class RunContext:
    """Mutable metadata container for one pipeline execution.

    A :class:`RunContext` is created by the caller (CLI command, API service,
    or batch processor) before calling
    :func:`~pptgen.pipeline.generate_presentation`.  It is passed as the
    optional ``run_context`` parameter and mutated in-place as each pipeline
    stage completes.

    Attributes:
        run_id:            Unique identifier for this execution.  Generated
                           automatically from a UUID4 hex if not supplied.
        request_id:        HTTP request identifier set at the API boundary.
                           ``None`` for CLI and batch invocations.
        profile:           Runtime profile string (``"dev"`` / ``"test"`` /
                           ``"prod"``).
        mode:              Execution mode (``"deterministic"`` or ``"ai"``).
        template_id:       Template ID override, if any.
        playbook_id:       Playbook chosen by the input router.  Populated
                           during pipeline execution.
        started_at:        UTC datetime when this context was created.
        timings:           Ordered list of :class:`StageTimer` records.
        workspace_path:    Absolute path to the per-run workspace directory,
                           once created.
        config_fingerprint: 8-character settings fingerprint from
                            :attr:`~pptgen.config.RuntimeSettings.fingerprint`.
    """

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    request_id: str | None = None
    profile: str = "dev"
    mode: str = "deterministic"
    template_id: str | None = None
    playbook_id: str | None = None
    started_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    timings: list[StageTimer] = field(default_factory=list)
    workspace_path: str | None = None
    config_fingerprint: str | None = None

    # ------------------------------------------------------------------
    # Stage timing
    # ------------------------------------------------------------------

    def start_stage(self, stage: str) -> None:
        """Record the start of *stage*.

        Creates a new :class:`StageTimer` and appends it to
        :attr:`timings`.  Call :meth:`end_stage` with the same name to
        record the completion time.
        """
        self.timings.append(StageTimer(stage=stage, started_at=time.monotonic()))

    def end_stage(self, stage: str) -> None:
        """Record the end of *stage*.

        Searches :attr:`timings` in reverse for an unfinished timer with
        the given stage name and sets its ``ended_at`` field.  If no
        matching timer is found (e.g. :meth:`start_stage` was never called
        for this stage), this method is a no-op.
        """
        for timer in reversed(self.timings):
            if timer.stage == stage and timer.ended_at is None:
                timer.ended_at = time.monotonic()
                return

    def total_ms(self) -> float:
        """Total elapsed milliseconds across all recorded timings.

        Returns 0.0 if no timings have been recorded.
        """
        if not self.timings:
            return 0.0
        last = max(
            (t.ended_at if t.ended_at is not None else time.monotonic())
            for t in self.timings
        )
        first = min(t.started_at for t in self.timings)
        return (last - first) * 1000

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def as_dict(self) -> dict:
        """Return a JSON-serialisable representation of this context.

        Suitable for structured logging, artifact metadata, and the API
        ``run_id`` response field.
        """
        return {
            "run_id": self.run_id,
            "request_id": self.request_id,
            "profile": self.profile,
            "mode": self.mode,
            "template_id": self.template_id,
            "playbook_id": self.playbook_id,
            "started_at": self.started_at.isoformat(),
            "timings": [
                {
                    "stage": t.stage,
                    "duration_ms": t.duration_ms,
                }
                for t in self.timings
            ],
            "total_ms": self.total_ms(),
            "config_fingerprint": self.config_fingerprint,
            "workspace_path": self.workspace_path,
        }
