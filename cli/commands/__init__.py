"""
CLI sub-commands package.
"""

from cli.commands.artifacts_cmd import artifacts_app
from cli.commands.auth_cmd import auth_app
from cli.commands.datasets_cmd import datasets_app
from cli.commands.inference_cmd import inference_app
from cli.commands.jobs_cmd import jobs_app
from cli.commands.models_cmd import models_app
from cli.commands.training_cmd import training_app
from cli.commands.workers_cmd import workers_app

__all__ = [
    "auth_app",
    "workers_app",
    "models_app",
    "datasets_app",
    "inference_app",
    "training_app",
    "jobs_app",
    "artifacts_app",
]
