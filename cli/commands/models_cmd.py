"""
Model Catalog and Direct Upload CLI Commands.
"""

from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.table import Table

from cli.auth import get_config
from cli.uploads import calculate_file_sha256, upload_file_with_progress

console = Console()
models_app = typer.Typer(help="Manage AI model manifests and upload model weights")


@models_app.command("list")
def list_models(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """List registered public and private model manifests."""
    cfg = get_config()
    token = cfg.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = f"{cfg['coordinator_url']}/api/v1/artifacts/models"

    try:
        with httpx.Client() as client:
            resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                console.print(f"[red]Error fetching models: {resp.text}[/red]")
                return

            models = resp.json()
            if json_output:
                console.print_json(data=models)
                return

            if not models:
                console.print("[yellow]No models found in catalog.[/yellow]")
                return

            table = Table(title="AI Model Catalog", show_header=True)
            table.add_column("Model ID", style="dim")
            table.add_column("Name", style="bold cyan")
            table.add_column("Architecture")
            table.add_column("Format")
            table.add_column("Required VRAM", justify="right")
            table.add_column("Public", justify="center")

            for m in models:
                table.add_row(
                    m["id"][:8],
                    m["name"],
                    m["architecture"],
                    m["format"],
                    f"{m['default_vram_required_mb']} MB",
                    "✓" if m["is_public"] else "✗",
                )

            console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")


@models_app.command("upload")
def upload_model(
    file_path: Path = typer.Argument(..., help="Path to local .safetensors model file"),
    name: str = typer.Option(..., "--name", "-n", help="Catalog name for the model"),
    architecture: str = typer.Option("LlamaForCausalLM", "--arch", "-a", help="Model architecture"),
    vram_mb: int = typer.Option(16384, "--vram", help="Required minimum VRAM in MB"),
    is_public: bool = typer.Option(False, "--public", help="Make model publicly available"),
) -> None:
    """Register and upload a Safetensors model weight bundle directly to object storage."""
    if not file_path.exists() or not file_path.is_file():
        console.print(f"[red]File {file_path} does not exist.[/red]")
        return

    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    base_url = cfg["coordinator_url"]

    # 1. Calculate SHA-256
    console.print(f"[*] Calculating SHA-256 checksum for {file_path.name}...")
    sha256, size_bytes = calculate_file_sha256(file_path)
    console.print(f"[green]✓ Checksum:[/green] {sha256} ({size_bytes / (1024 * 1024):.1f} MB)")

    try:
        with httpx.Client() as client:
            # 2. Create Model Manifest
            console.print("[*] Registering model manifest...")
            manifest_resp = client.post(
                f"{base_url}/api/v1/artifacts/models",
                headers=headers,
                json={
                    "name": name,
                    "architecture": architecture,
                    "framework": "transformers",
                    "format": "safetensors",
                    "default_vram_required_mb": vram_mb,
                    "is_public": is_public,
                },
            )
            if manifest_resp.status_code not in [200, 201]:
                console.print(f"[red]Failed to register manifest: {manifest_resp.text}[/red]")
                return

            model_id = manifest_resp.json()["id"]

            # 3. Request Pre-signed S3 Upload URL
            console.print("[*] Requesting pre-signed direct upload URL...")
            url_resp = client.post(
                f"{base_url}/api/v1/artifacts/models/{model_id}/upload-url",
                headers=headers,
                json={
                    "filename": file_path.name,
                    "size_bytes": size_bytes,
                    "checksum_sha256": sha256,
                },
            )
            if url_resp.status_code != 200:
                console.print(f"[red]Failed to get upload URL: {url_resp.text}[/red]")
                return

            upload_url = url_resp.json()["upload_url"]

            # 4. Stream Upload to MinIO/S3 with Progress Bar
            upload_file_with_progress(upload_url, file_path)
            console.print(
                f"[bold green]✓ Successfully uploaded {name} (ID: {model_id})![/bold green]"
            )

    except Exception as e:
        console.print(f"[red]Upload failed: {e}[/red]")
