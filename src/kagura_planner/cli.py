from __future__ import annotations

import typer

from . import __version__
from .config import ConfigError, load_config
from .doctor.registry import overall_status, run_all
from .doctor.render import print_table, to_json
from .doctor.result import Status

app = typer.Typer(help="Memory-grounded PLAN-layer CLI over Claude Code + Kagura Memory.")

_CONFIG_OPT = typer.Option("repo.yaml", "--config", "-c", help="path to repo.yaml")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def _main(
    version: bool = typer.Option(
        False, "--version", help="Show the kagura-planner version and exit.",
        callback=_version_callback, is_eager=True,
    ),
) -> None:
    """Memory-grounded PLAN-layer CLI over Claude Code + Kagura Memory."""


@app.command()
def doctor(config: str = _CONFIG_OPT, json_out: bool = typer.Option(False, "--json")) -> None:
    """Check the dependency chain (git, claude-code, memory, planning skills)."""
    try:
        cfg = load_config(config)
    except ConfigError as exc:
        typer.echo(f"doctor: invalid config '{config}': {exc}", err=True)
        raise typer.Exit(code=2)
    results = run_all(cfg)
    typer.echo(to_json(results)) if json_out else print_table(results)
    if overall_status(results) is Status.FAIL:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
