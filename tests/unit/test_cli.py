"""
Unit tests for the CloudAI Typer CLI Client.
"""

from typer.testing import CliRunner

from cli.client import app

runner = CliRunner()


def test_cli_help() -> None:
    """Verify top-level CLI help prints available commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Decentralized Community AI Compute Cloud Platform CLI" in result.stdout
    assert "workers" in result.stdout
    assert "inference" in result.stdout
    assert "training" in result.stdout
    assert "jobs" in result.stdout


def test_cli_subcommands_help() -> None:
    """Verify sub-command help screens."""
    res_workers = runner.invoke(app, ["workers", "--help"])
    assert res_workers.exit_code == 0
    assert "Inspect and manage GPU compute providers" in res_workers.stdout

    res_infer = runner.invoke(app, ["inference", "--help"])
    assert res_infer.exit_code == 0
    assert "Execute text and image inference" in res_infer.stdout

    res_jobs = runner.invoke(app, ["jobs", "--help"])
    assert res_jobs.exit_code == 0
    assert "Monitor and cancel compute jobs" in res_jobs.stdout
