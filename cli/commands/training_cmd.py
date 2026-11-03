"""
Fine-Tuning and Distributed Training CLI Commands.
"""

from uuid import UUID

import httpx
import typer
from rich.console import Console

from cli.auth import get_config

console = Console()
training_app = typer.Typer(help="Manage parameter-efficient LoRA fine-tuning workloads")


@training_app.command("lora")
def train_lora(
    model: str = typer.Option(
        "mistralai/Mistral-7B-v0.1", "--model", "-m", help="Base model repository or manifest name"
    ),
    dataset_id: UUID = typer.Option(..., "--dataset", "-d", help="Catalog dataset UUID"),
    rank: int = typer.Option(16, "--rank", "-r", help="LoRA rank dimension"),
    alpha: int = typer.Option(32, "--alpha", "-a", help="LoRA alpha scaling factor"),
    epochs: int = typer.Option(3, "--epochs", "-e", help="Training epochs"),
    lr: float = typer.Option(2e-4, "--lr", help="Learning rate"),
) -> None:
    """Submit a PEFT LoRA fine-tuning workload to qualified community GPUs."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{cfg['coordinator_url']}/api/v1/jobs/training/lora"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                url,
                headers=headers,
                json={
                    "model_name": model,
                    "dataset_id": str(dataset_id),
                    "lora_r": rank,
                    "lora_alpha": alpha,
                    "epochs": epochs,
                    "learning_rate": lr,
                },
            )
            if resp.status_code != 201:
                console.print(f"[red]Training submission failed: {resp.text}[/red]")
                return

            job = resp.json()
            console.print(
                f"[bold green]✓ LoRA training job created![/bold green] (Job ID: [cyan]{job['id']}[/cyan])"
            )
            console.print(
                f"[dim]Status: {job['status']} | Worker: {job.get('assigned_worker_id') or 'Matching GPU...'}[/dim]"
            )
            console.print(f"[dim]Live stream: 'cloudai jobs logs {job['id']} --follow'[/dim]")

    except Exception as e:
        console.print(f"[red]Connection error: {e}[/red]")
