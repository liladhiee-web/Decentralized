"""
Job Monitoring, Cancellation, and Live Logs CLI Commands.
"""

from uuid import UUID

import httpx
import typer
from rich.console import Console
from rich.table import Table

from cli.auth import get_config

console = Console()
jobs_app = typer.Typer(help="Monitor, query, stream logs, and cancel compute jobs")


@jobs_app.command("list")
def list_jobs(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    job_type: str | None = typer.Option(None, "--type", "-t", help="Filter by type"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List recent AI inference and training jobs."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{cfg['coordinator_url']}/api/v1/jobs"
    params = {}
    if status:
        params["status"] = status
    if job_type:
        params["type"] = job_type

    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                console.print(f"[red]Failed to list jobs: {resp.text}[/red]")
                return

            data = resp.json()
            if json_output:
                console.print_json(data=data)
                return

            jobs = data.get("jobs", [])
            if not jobs:
                console.print("[yellow]No jobs found matching criteria.[/yellow]")
                return

            table = Table(title="AI Compute Jobs", show_header=True)
            table.add_column("Job ID", style="dim")
            table.add_column("Type", style="cyan")
            table.add_column("Status")
            table.add_column("Cost (Credits)", justify="right")
            table.add_column("Created At")

            for j in jobs:
                status_color = (
                    "green"
                    if j["status"] == "completed"
                    else "yellow"
                    if j["status"] in ["running", "dispatched"]
                    else "red"
                    if j["status"] == "failed"
                    else "white"
                )
                table.add_row(
                    j["id"][:8],
                    j["type"],
                    f"[{status_color}]{j['status'].upper()}[/{status_color}]",
                    f"{j['execution_cost_credits']:.4f}",
                    j["created_at"][:19],
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@jobs_app.command("status")
def job_status(job_id: UUID = typer.Argument(..., help="Job UUID")) -> None:
    """Retrieve detailed state and events for a job."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{cfg['coordinator_url']}/api/v1/jobs/{job_id}"

    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                console.print(f"[red]Job not found: {resp.text}[/red]")
                return

            job = resp.json()
            console.print(f"[bold cyan]Job ID:[/bold cyan] {job['id']}")
            console.print(f"[bold]Type:[/bold] {job['type']}")
            console.print(f"[bold]Status:[/bold] {job['status']}")
            console.print(f"[bold]Worker:[/bold] {job.get('assigned_worker_id') or 'Unassigned'}")
            console.print(f"[bold]Cost:[/bold] {job['execution_cost_credits']:.4f} credits")

            if job.get("events"):
                console.print("\n[bold]Execution Audit Trail:[/bold]")
                for ev in job["events"]:
                    console.print(
                        f"  • [{ev['timestamp'][:19]}] [bold]{ev['event_type']}[/bold] - {ev['details']}"
                    )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@jobs_app.command("logs")
def job_logs(
    job_id: UUID = typer.Argument(..., help="Job UUID"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow live output stream"),
) -> None:
    """Stream real-time execution logs from the assigned worker."""
    cfg = get_config()
    token = cfg.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{cfg['coordinator_url']}/api/v1/jobs/{job_id}/stream"

    try:
        with httpx.Client(timeout=3600.0) as client:
            with client.stream("GET", url, headers=headers) as stream:
                for line in stream.iter_lines():
                    if line.startswith("data: "):
                        console.print(f"[dim]>[/dim] {line[6:]}")
                    if not follow and "completed" in line:
                        break
    except Exception as e:
        console.print(f"[red]Log stream error: {e}[/red]")


@jobs_app.command("cancel")
def cancel_job(job_id: UUID = typer.Argument(..., help="Job UUID")) -> None:
    """Request immediate cancellation of a running or queued job."""
    cfg = get_config()
    token = cfg.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{cfg['coordinator_url']}/api/v1/jobs/{job_id}/cancel"

    try:
        with httpx.Client() as client:
            resp = client.post(url, headers=headers)
            if resp.status_code == 200:
                console.print(f"[green]✓ Cancellation requested for job {job_id}[/green]")
            else:
                console.print(f"[red]Cancellation failed: {resp.text}[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
