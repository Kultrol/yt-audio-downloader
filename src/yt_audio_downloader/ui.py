from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

console = Console()


def ok(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def info(message: str) -> None:
    console.print(f"[cyan]›[/cyan] {message}")


def warn(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}")


def error(message: str) -> None:
    console.print("[red]✗[/red] ", end="")
    console.print(message, markup=False)


def download_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def track_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        console=console,
        transient=False,
    )
