"""CLI commands for run inspection — Stage 6D."""
from __future__ import annotations

import json
from typing import Optional

import typer

from ..config import get_settings
from ..runs.sqlite_store import SQLiteRunStore

run_app = typer.Typer(name="runs", help="Inspect run history.")


def _get_store() -> SQLiteRunStore:
    settings = get_settings()
    return SQLiteRunStore.from_settings(settings)


@run_app.command("list")
def list_runs(
    limit: int = typer.Option(20, help="Max runs to show."),
    offset: int = typer.Option(0, help="Pagination offset."),
    status: Optional[str] = typer.Option(None, help="Filter by status (running/succeeded/failed)."),
    source: Optional[str] = typer.Option(None, help="Filter by source (api_sync/api_async/cli/batch)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List recent pipeline runs."""
    store = _get_store()
    try:
        runs = store.list_runs(limit=limit, offset=offset, status=status, source=source)
        if json_output:
            typer.echo(json.dumps([{
                "run_id": r.run_id,
                "status": r.status.value,
                "source": r.source.value,
                "total_ms": r.total_ms,
                "artifact_count": r.artifact_count,
                "started_at": r.started_at.isoformat(),
            } for r in runs], indent=2))
        else:
            if not runs:
                typer.echo("No runs found.")
                return
            typer.echo(f"{'RUN_ID':<34} {'STATUS':<12} {'SOURCE':<12} {'MS':>8}  STARTED")
            for r in runs:
                ms = f"{r.total_ms:.0f}" if r.total_ms is not None else "-"
                typer.echo(
                    f"{r.run_id:<34} {r.status.value:<12} {r.source.value:<12} {ms:>8}  {r.started_at.isoformat()[:19]}"
                )
    finally:
        store.close()


@run_app.command("show")
def show_run(
    run_id: str,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show full details for a run."""
    store = _get_store()
    try:
        run = store.get(run_id)
        if run is None:
            typer.echo(f"Run not found: {run_id}", err=True)
            raise typer.Exit(1)
        if json_output:
            data = {
                "run_id": run.run_id,
                "status": run.status.value,
                "source": run.source.value,
                "job_id": run.job_id,
                "playbook_id": run.playbook_id,
                "template_id": run.template_id,
                "started_at": run.started_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "total_ms": run.total_ms,
                "artifact_count": run.artifact_count,
                "error_category": run.error_category,
                "error_message": run.error_message,
                "manifest_path": run.manifest_path,
            }
            typer.echo(json.dumps(data, indent=2))
        else:
            typer.echo(f"Run ID:        {run.run_id}")
            typer.echo(f"Status:        {run.status.value}")
            typer.echo(f"Source:        {run.source.value}")
            typer.echo(f"Job ID:        {run.job_id or '-'}")
            typer.echo(f"Playbook:      {run.playbook_id or '-'}")
            typer.echo(f"Template:      {run.template_id or '-'}")
            typer.echo(f"Started:       {run.started_at.isoformat()}")
            typer.echo(f"Completed:     {run.completed_at.isoformat() if run.completed_at else '-'}")
            typer.echo(f"Total ms:      {run.total_ms if run.total_ms is not None else '-'}")
            typer.echo(f"Artifact cnt:  {run.artifact_count if run.artifact_count is not None else '-'}")
            if run.error_category:
                typer.echo(f"Error:         [{run.error_category}] {run.error_message}")
    finally:
        store.close()


@run_app.command("metrics")
def show_metrics(
    run_id: str,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Show stage timing metrics for a run."""
    store = _get_store()
    try:
        run = store.get(run_id)
        if run is None:
            typer.echo(f"Run not found: {run_id}", err=True)
            raise typer.Exit(1)
        timings = run.stage_timings or []
        if json_output:
            typer.echo(json.dumps({
                "run_id": run.run_id,
                "total_ms": run.total_ms,
                "artifact_count": run.artifact_count,
                "stage_timings": timings,
            }, indent=2))
        else:
            total = run.total_ms if run.total_ms is not None else "-"
            cnt = run.artifact_count if run.artifact_count is not None else "-"
            typer.echo(f"Run: {run.run_id}  total={total} ms  artifacts={cnt}")
            if not timings:
                typer.echo("  No stage timings recorded.")
            else:
                typer.echo(f"\n  {'STAGE':<30} {'MS':>10}")
                for t in timings:
                    ms = f"{t['duration_ms']:.1f}" if t.get("duration_ms") is not None else "-"
                    typer.echo(f"  {t['stage']:<30} {ms:>10}")
    finally:
        store.close()
