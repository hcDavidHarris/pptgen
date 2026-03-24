"""CLI commands for async job queue — Stage 6B."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ..config import get_settings
from ..jobs.models import JobRecord, WorkloadType
from ..jobs.sqlite_store import SQLiteJobStore

job_app = typer.Typer(name="job", help="Manage async presentation generation jobs.")


def _get_store() -> SQLiteJobStore:
    settings = get_settings()
    return SQLiteJobStore.from_settings(settings)


@job_app.command("submit")
def submit(
    input_file: Path = typer.Argument(..., help="Path to input text file"),
    template: str = typer.Option(None, "--template", "-t", help="Template ID"),
    batch: bool = typer.Option(False, "--batch", help="Use batch priority (lower)"),
    artifacts: bool = typer.Option(False, "--artifacts", help="Export pipeline artifacts"),
) -> None:
    """Submit a presentation generation job to the async queue."""
    if not input_file.exists():
        typer.echo(f"Error: File not found: {input_file}", err=True)
        raise typer.Exit(1)

    input_text = input_file.read_text(encoding="utf-8")
    wt = WorkloadType.BATCH if batch else WorkloadType.INTERACTIVE
    job = JobRecord.create(
        input_text=input_text,
        workload_type=wt,
        template_id=template,
        artifacts=artifacts,
    )
    store = _get_store()
    try:
        store.submit(job)
        typer.echo(f"Submitted job: {job.job_id}")
        typer.echo(f"Status: {job.status.value}")
    finally:
        store.close()


@job_app.command("status")
def status(
    job_id: str = typer.Argument(..., help="Job ID to look up"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Check the status of a submitted job."""
    store = _get_store()
    try:
        job = store.get(job_id)
        if job is None:
            typer.echo(f"Error: Job not found: {job_id}", err=True)
            raise typer.Exit(1)

        if json_output:
            typer.echo(json.dumps({
                "job_id": job.job_id,
                "status": job.status.value,
                "retry_count": job.retry_count,
                "error_category": job.error_category,
                "error_message": job.error_message,
                "output_path": job.output_path,
                "playbook_id": job.playbook_id,
            }, indent=2))
        else:
            typer.echo(f"Job:     {job.job_id}")
            typer.echo(f"Status:  {job.status.value}")
            if job.output_path:
                typer.echo(f"Output:  {job.output_path}")
            if job.error_message:
                typer.echo(f"Error:   {job.error_message}")
    finally:
        store.close()
