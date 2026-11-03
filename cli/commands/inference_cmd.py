"""
AI Inference CLI Commands.
Dispatches text generation and diffusion image synthesis jobs.
"""

from pathlib import Path

import httpx
import typer
from rich.console import Console

from cli.auth import get_config

console = Console()
inference_app = typer.Typer(help="Execute text generation and image synthesis inference")


@inference_app.command("text")
def inference_text(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Text input prompt"),
    model: str = typer.Option(
        "meta-llama/Llama-3-8B-Instruct", "--model", "-m", help="Model name or ID"
    ),
    max_tokens: int = typer.Option(256, "--max-tokens", help="Maximum tokens to generate"),
    temperature: float = typer.Option(0.7, "--temp", help="Sampling temperature"),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream tokens via SSE"),
) -> None:
    """Submit a text generation inference job to community GPUs."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{cfg['coordinator_url']}/api/v1/jobs/inference/text"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                url,
                headers=headers,
                json={
                    "model_name": model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": stream,
                },
            )
            if resp.status_code != 201:
                console.print(f"[red]Job submission failed: {resp.text}[/red]")
                return

            job = resp.json()
            job_id = job["id"]
            console.print(
                f"[green]✓ Job submitted successfully![/green] (Job ID: [bold]{job_id}[/bold])"
            )
            console.print(
                f"[dim]Status: {job['status']} | Worker: {job.get('assigned_worker_id') or 'Scheduling...'}[/dim]"
            )

            if stream:
                console.print("[*] Connecting to live token stream...")
                stream_url = f"{cfg['coordinator_url']}/api/v1/jobs/{job_id}/stream"
                with client.stream(
                    "GET", stream_url, headers=headers, timeout=600.0
                ) as stream_resp:
                    for line in stream_resp.iter_lines():
                        if line.startswith("data: "):
                            raw_data = line[6:]
                            console.print(raw_data)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@inference_app.command("image")
def inference_image(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Image prompt description"),
    steps: int = typer.Option(30, "--steps", help="Number of inference steps"),
    output: Path = typer.Option(Path("./output.png"), "--output", "-o", help="Output file path"),
) -> None:
    """Submit a Stable Diffusion / Diffusers image synthesis job."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[red]Authentication required. Run 'cloudai login'.[/red]")
        return

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{cfg['coordinator_url']}/api/v1/jobs/inference/image"

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                url,
                headers=headers,
                json={
                    "prompt": prompt,
                    "num_inference_steps": steps,
                },
            )
            if resp.status_code != 201:
                console.print(f"[red]Failed to submit image job: {resp.text}[/red]")
                return

            job = resp.json()
            console.print(
                f"[green]✓ Image job submitted![/green] (Job ID: [bold]{job['id']}[/bold])"
            )
            console.print(f"[dim]Monitor with: 'cloudai jobs logs {job['id']} --follow'[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
