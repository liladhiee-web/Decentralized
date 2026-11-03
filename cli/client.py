"""
CloudAI CLI Client Main Entrypoint.
Provides a unified developer command-line interface for the decentralized compute platform.
"""

import typer
from rich.console import Console

from cli.commands.artifacts_cmd import artifacts_app
from cli.commands.auth_cmd import auth_app, login, register, whoami
from cli.commands.datasets_cmd import datasets_app
from cli.commands.inference_cmd import inference_app
from cli.commands.jobs_cmd import jobs_app
from cli.commands.models_cmd import models_app
from cli.commands.training_cmd import training_app
from cli.commands.workers_cmd import workers_app

console = Console()

app = typer.Typer(
    name="cloudai",
    help="Decentralized Community AI Compute Cloud Platform CLI",
    add_completion=True,
    no_args_is_help=True,
)

# Top-level direct shortcuts
app.command("register", help="Register a new CloudAI account")(register)
app.command("login", help="Authenticate with email & password")(login)
app.command("whoami", help="Display current account and credit balance")(whoami)

# Mount command groups
app.add_typer(auth_app, name="auth", help="Authentication and session management")
app.add_typer(workers_app, name="workers", help="Inspect and manage GPU compute providers")
app.add_typer(models_app, name="models", help="Model catalog and weight uploads")
app.add_typer(datasets_app, name="datasets", help="Fine-tuning dataset uploads")
app.add_typer(inference_app, name="inference", help="Execute text and image inference")
app.add_typer(training_app, name="training", help="Submit LoRA fine-tuning workloads")
app.add_typer(jobs_app, name="jobs", help="Monitor and cancel compute jobs")
app.add_typer(artifacts_app, name="artifacts", help="Download trained checkpoints and outputs")


def main() -> None:
    """Entrypoint function for CLI executable."""
    app()


if __name__ == "__main__":
    main()
