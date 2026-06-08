from __future__ import annotations

from datetime import date as _date

import typer

from . import __version__
from .config import ConfigError, load_config
from .doctor.registry import overall_status, run_all
from .doctor.render import print_table, to_json
from .doctor.result import Status
from .plan import STATUS_EXIT, plan_idea
from .plan.render import print_table as plan_print_table
from .plan.render import to_json as plan_to_json

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


@app.command()
def plan(
    idea: str = typer.Argument(..., help="the idea/goal to plan"),
    config: str = _CONFIG_OPT,
    no_remember: bool = typer.Option(False, "--no-remember", help="skip memory persist (recall still happens)"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Produce a memory-grounded plan doc from an idea.

    Exit codes: 0 = plan written · 1 = hard fail · 2 = blocked (env guard).
    """
    try:
        cfg = load_config(config)
    except ConfigError as exc:
        typer.echo(f"plan: invalid config '{config}': {exc}", err=True)
        raise typer.Exit(code=2)
    report = plan_idea(cfg, idea, date=_date.today().isoformat(), no_remember=no_remember)
    typer.echo(plan_to_json(report)) if json_out else plan_print_table(report)
    raise typer.Exit(code=STATUS_EXIT[report.status])


if __name__ == "__main__":
    app()
