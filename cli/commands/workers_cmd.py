"""
GPU Compute Worker Marketplace CLI Commands.
"""

import httpx
import typer
from rich.console import Console
from rich.table import Table

from cli.auth import get_config

console = Console()
workers_app = typer.Typer(help="Inspect registered GPU workers and compute capacity")


@workers_app.command("list")
def list_workers(
    status: str | None = typer.Option(None, help="Filter by status: idle, busy, offline"),
    json_output: bool = typer.Option(False, "--json", help="Print raw JSON format"),
) -> None:
    """List active GPU workers in the community compute cloud."""
    cfg = get_config()
    token = cfg.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{cfg['coordinator_url']}/api/v1/workers"
    params = {"status": status} if status else {}

    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                console.print(f"[red]Error fetching workers: {resp.text}[/red]")
                return

            workers = resp.json()
            if json_output:
                console.print_json(data=workers)
                return

            if not workers:
                console.print("[yellow]No GPU workers currently registered.[/yellow]")
                return

            table = Table(title="Community GPU Compute Providers", show_header=True)
            table.add_column("Worker ID", style="dim", overflow="ellipsis")
            table.add_column("Name", style="bold")
            table.add_column("Status")
            table.add_column("GPU Model", style="cyan")
            table.add_column("VRAM (Total / Free)", justify="right")
            table.add_column("Temp (°C)", justify="right")
            table.add_column("Jobs Done", justify="right")

            for w in workers:
                status_color = (
                    "green"
                    if w["status"] == "idle"
                    else "yellow"
                    if w["status"] == "busy"
                    else "red"
                )
                status_str = f"[{status_color}]{w['status'].upper()}[/{status_color}]"

                gpu_name = "N/A"
                vram_str = "N/A"
                temp_str = "N/A"

                if w.get("gpu_devices"):
                    first_gpu = w["gpu_devices"][0]
                    gpu_name = first_gpu["name"]
                    vram_str = f"{first_gpu['total_vram_mb']}MB / {first_gpu['free_vram_mb']}MB"
                    temp_str = f"{first_gpu['temperature_celsius']:.1f}°C"

                table.add_row(
                    w["id"][:8],
                    w["name"],
                    status_str,
                    gpu_name,
                    vram_str,
                    temp_str,
                    str(w.get("total_jobs_completed", 0)),
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")
