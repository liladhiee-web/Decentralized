"""
Authentication and Profile CLI Commands.
"""

import httpx
import typer
from rich.console import Console

from cli.auth import clear_credentials, get_config, set_credentials

console = Console()
auth_app = typer.Typer(help="User registration, login, and authentication management")


@auth_app.command("register")
def register(
    email: str = typer.Option(..., prompt=True, help="Your account email address"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password (min 8 chars)"),
    full_name: str | None = typer.Option(None, help="Full name or company name"),
    role: str = typer.Option("user", help="Account role: 'user' or 'provider'"),
) -> None:
    """Register a new CloudAI account."""
    cfg = get_config()
    url = f"{cfg['coordinator_url']}/api/v1/auth/register"

    try:
        with httpx.Client() as client:
            resp = client.post(
                url,
                json={"email": email, "password": password, "full_name": full_name, "role": role},
            )
            if resp.status_code == 201:
                console.print(f"[green]✓ Successfully registered account for {email}![/green]")
                console.print("[dim]Use 'cloudai login' to authenticate.[/dim]")
            else:
                console.print(f"[red]Registration failed: {resp.text}[/red]")
    except Exception as e:
        console.print(f"[red]Network error connecting to coordinator: {e}[/red]")


@auth_app.command("login")
def login(
    email: str = typer.Option(..., prompt=True, help="Account email"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password"),
) -> None:
    """Authenticate and store session tokens locally."""
    cfg = get_config()
    url = f"{cfg['coordinator_url']}/api/v1/auth/login"

    try:
        with httpx.Client() as client:
            resp = client.post(url, json={"email": email, "password": password})
            if resp.status_code == 200:
                data = resp.json()
                set_credentials(
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    email=email,
                )
                console.print(f"[green]✓ Authenticated as {email} successfully![/green]")
            else:
                console.print(f"[red]Login failed: {resp.text}[/red]")
    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")


@auth_app.command("whoami")
def whoami() -> None:
    """Display currently authenticated profile and balance."""
    cfg = get_config()
    token = cfg.get("access_token")
    if not token:
        console.print("[yellow]Not logged in. Run 'cloudai login'.[/yellow]")
        return

    url = f"{cfg['coordinator_url']}/api/v1/auth/me"
    try:
        with httpx.Client() as client:
            resp = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                user = resp.json()
                console.print(f"[bold cyan]User:[/bold cyan] {user['email']}")
                console.print(f"[bold cyan]Role:[/bold cyan] {user['role']}")
                console.print(
                    f"[bold cyan]Balance:[/bold cyan] {user['balance_credits']:.2f} credits"
                )
            else:
                console.print("[red]Session expired. Please log in again.[/red]")
    except Exception as e:
        console.print(f"[red]Failed to connect: {e}[/red]")


@auth_app.command("logout")
def logout() -> None:
    """Clear local credentials."""
    clear_credentials()
    console.print("[green]✓ Session cleared.[/green]")
