"""
Artifact Inspection and Download CLI Commands.
"""

from pathlib import Path
from uuid import UUID

import httpx
import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

from cli.auth import get_config

console = Console()
artifacts_app = typer.Typer(
    help="Inspect and download trained adapters, checkpoints, and generated images"
)


@artifacts_app.command("list")
def list_artifacts(
    job_id: UUID | None = typer.Option(None, "--job-id", "-j", help="Filter by Job UUID"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List output artifacts created by completed jobs."""
    cfg = get_config()
    token = cfg.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{cfg['coordinator_url']}/api/v1/artifacts"
    params = {"job_id": str(job_id)} if job_id else {}

    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code != 200:
                console.print(f"[red]Error fetching artifacts: {resp.text}[/red]")
                return

            artifacts = resp.json()
            if json_output:
                console.print_json(data=artifacts)
                return

            if not artifacts:
                console.print("[yellow]No artifacts found.[/yellow]")
                return

            table = Table(title="Generated Artifacts & Model Outputs", show_header=True)
            table.add_column("Artifact ID", style="dim")
            table.add_column("Filename", style="bold cyan")
            table.add_column("Type")
            table.add_column("Size", justify="right")
            table.add_column("Created At")

            for a in artifacts:
                size_mb = round(a["size_bytes"] / (1024 * 1024), 2)
                table.add_row(
                    a["id"][:8],
                    a["filename"],
                    a["artifact_type"],
                    f"{size_mb} MB",
                    a["created_at"][:19],
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@artifacts_app.command("download")
def download_artifact(
    artifact_id: UUID = typer.Argument(..., help="Artifact UUID to download"),
    output_dir: Path = typer.Option(Path("./"), "--output", "-o", help="Target output directory"),
) -> None:
    """Download an artifact directly from S3/MinIO via a short-lived signed URL."""
    cfg = get_config()
    token = cfg.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    base_url = cfg["coordinator_url"]

    try:
        with httpx.Client() as client:
            # 1. Fetch pre-signed download URL
            resp = client.get(
                f"{base_url}/api/v1/artifacts/{artifact_id}/download-url",
                headers=headers,
            )
            if resp.status_code != 200:
                console.print(f"[red]Failed to get download URL: {resp.text}[/red]")
                return

            data = resp.json()
            download_url = data["download_url"]
            filename = data["filename"]
            target_file = output_dir / filename
            output_dir.mkdir(parents=True, exist_ok=True)

            # 2. Download with Rich progress bar
            with client.stream("GET", download_url) as dl_resp:
                if dl_resp.status_code != 200:
                    console.print(f"[red]Download failed with HTTP {dl_resp.status_code}[/red]")
                    return

                total_bytes = int(dl_resp.headers.get("Content-Length", 0))

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                ) as progress:
                    task = progress.add_task(f"Downloading {filename}", total=total_bytes)
                    with open(target_file, "wb") as f:
                        for chunk in dl_resp.iter_bytes(chunk_size=65536):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))

            console.print(f"[bold green]✓ Downloaded to {target_file.resolve()}![/bold green]")

    except Exception as e:
        console.print(f"[red]Download error: {e}[/red]")
