from __future__ import annotations

import typer

from . import __version__

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


if __name__ == "__main__":
    app()
