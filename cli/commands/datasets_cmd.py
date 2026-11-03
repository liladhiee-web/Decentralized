"""
Dataset Catalog and Upload CLI Commands.
"""

from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.table import Table

from cli.auth import get_config
from cli.uploads import calculate_file_sha256, upload_file_with_progress

console = Console()
datasets_app = typer.Typer(help="Manage fine-tuning and evaluation datasets")


@datasets_app.command("list")
def list_datasets(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List datasets owned by current user."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[yellow]Authentication required. Run 'cloudai login'.[/yellow]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{cfg['coordinator_url']}/api/v1/artifacts/datasets"

    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                console.print(f"[red]Error fetching datasets: {resp.text}[/red]")
                return

            datasets = resp.json()
            if json_output:
                console.print_json(data=datasets)
                return

            if not datasets:
                console.print("[yellow]No datasets uploaded yet.[/yellow]")
                return

            table = Table(title="Uploaded Training Datasets", show_header=True)
            table.add_column("Dataset ID", style="dim")
            table.add_column("Name", style="bold cyan")
            table.add_column("Format")
            table.add_column("Size", justify="right")
            table.add_column("Records", justify="right")

            for d in datasets:
                size_mb = round(d["size_bytes"] / (1024 * 1024), 2)
                table.add_row(
                    d["id"][:8],
                    d["name"],
                    d["format"],
                    f"{size_mb} MB",
                    str(d.get("num_records", 0)),
                )

            console.print(table)
    except Exception as e:
        console.print(f"[red]Connection error: {e}[/red]")


@datasets_app.command("upload")
def upload_dataset(
    file_path: Path = typer.Argument(..., help="Path to local dataset file (.jsonl, .parquet)"),
    name: str = typer.Option(..., "--name", "-n", help="Dataset name"),
    format_type: str = typer.Option("jsonl", "--format", "-f", help="Format: jsonl or parquet"),
) -> None:
    """Upload a training dataset to S3/MinIO."""
    if not file_path.exists() or not file_path.is_file():
        console.print(f"[red]File {file_path} not found.[/red]")
        return

    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    base_url = cfg["coordinator_url"]

    console.print(f"[*] Hashing {file_path.name}...")
    sha256, size_bytes = calculate_file_sha256(file_path)

    try:
        with httpx.Client() as client:
            # 1. Register Dataset Entry
            reg_resp = client.post(
                f"{base_url}/api/v1/artifacts/datasets",
                headers=headers,
                json={
                    "name": name,
                    "format": format_type,
                    "size_bytes": size_bytes,
                    "checksum_sha256": sha256,
                },
            )
            if reg_resp.status_code not in [200, 201]:
                console.print(f"[red]Failed to register dataset: {reg_resp.text}[/red]")
                return

            dataset_id = reg_resp.json()["id"]

            # 2. Get Presigned Upload URL
            url_resp = client.post(
                f"{base_url}/api/v1/artifacts/datasets/{dataset_id}/upload-url",
                headers=headers,
            )
            if url_resp.status_code != 200:
                console.print(f"[red]Failed to obtain upload URL: {url_resp.text}[/red]")
                return

            upload_url = url_resp.json()["upload_url"]

            # 3. Stream Upload
            upload_file_with_progress(upload_url, file_path)
            console.print(
                f"[bold green]✓ Successfully uploaded dataset {name} (ID: {dataset_id})![/bold green]"
            )

    except Exception as e:
        console.print(f"[red]Upload error: {e}[/red]")
