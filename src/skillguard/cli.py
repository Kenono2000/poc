"""Typer CLI for SkillGuard."""

import json
from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from skillguard.analyzer import analyze
from skillguard.scanner import scan_skills
from skillguard.web import create_app

app = typer.Typer(help="SkillGuard: Manage agent skills, evaluate conflicts, and predict problems.")
console = Console()


@app.command()
def scan(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root directory."),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """List discovered global and project-specific skills."""
    skills = scan_skills(project_dir=project.resolve())
    if as_json:
        typer.echo(json.dumps([s.to_dict() for s in skills], indent=2))
        return

    table = Table(title=f"Discovered Skills ({len(skills)})")
    table.add_column("Scope", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold white")
    table.add_column("Tokens", justify="right")
    table.add_column("Guardrail", justify="center")
    table.add_column("Description", max_width=60)

    for s in skills:
        table.add_row(
            s.scope,
            s.name,
            str(s.token_count),
            "yes" if s.has_negative_guardrail else "no",
            (s.description[:57] + "...") if len(s.description) > 60 else s.description,
        )
    console.print(table)


@app.command()
def check(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root directory."),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Evaluate skill conflicts and predict potential problems."""
    skills = scan_skills(project_dir=project.resolve())
    result = analyze(skills)

    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
        return

    console.print(f"[bold]Skills:[/bold] {len(result.skills)} | [bold]Total Tokens:[/bold] {result.total_tokens}")

    if result.conflicts:
        ctable = Table(title=f"Conflicts ({len(result.conflicts)})")
        ctable.add_column("Severity", style="bold")
        ctable.add_column("Type")
        ctable.add_column("Skills")
        ctable.add_column("Message")
        for c in result.conflicts:
            color = "red" if c.severity == "critical" else "yellow"
            ctable.add_row(f"[{color}]{c.severity}[/{color}]", c.conflict_type, ", ".join(c.skills), c.message)
        console.print(ctable)
    else:
        console.print("[green]No skill conflicts detected.[/green]")

    if result.predictions:
        ptable = Table(title=f"Predicted Problems ({len(result.predictions)})")
        ptable.add_column("Severity", style="bold")
        ptable.add_column("Risk", justify="right")
        ptable.add_column("Target")
        ptable.add_column("Message")
        for p in result.predictions:
            color = "red" if p.severity == "critical" else ("yellow" if p.severity == "warning" else "dim")
            ptable.add_row(f"[{color}]{p.severity}[/{color}]", str(p.risk_score), p.target, p.message)
        console.print(ptable)
    else:
        console.print("[green]No skill problems predicted.[/green]")


@app.command()
def ui(
    project: Path = typer.Option(Path("."), "--project", "-p", help="Project root directory."),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host."),
    port: int = typer.Option(8765, "--port", help="Bind port."),
) -> None:
    """Launch the embedded SkillGuard web dashboard."""
    web_app = create_app(project_dir=project.resolve())
    console.print(f"[cyan]SkillGuard Dashboard running at http://{host}:{port}[/cyan]")
    uvicorn.run(web_app, host=host, port=port, log_level="warning")
