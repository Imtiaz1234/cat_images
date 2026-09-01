"""Command-line interface for mdpub."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import uvicorn

from mdpub.config import list_presets
from mdpub.pipeline import PolishOptions, iter_markdown_files, polish_path

app = typer.Typer(
    name="mdpub",
    help="Polish Markdown files into blog-ready, publishable posts.",
    no_args_is_help=True,
)

PresetOption = typer.Option("generic", "--preset", "-p", help="Frontmatter preset: generic, hugo, jekyll, astro")
AiOption = typer.Option(False, "--ai", help="Fill missing metadata with an OpenAI-compatible model")
SiteOption = typer.Option(None, "--site-url", help="Base URL used to build canonical links")
TocOption = typer.Option(False, "--toc", help="Insert a table of contents after the H1")


def _validate_preset(preset: str) -> str:
    try:
        known = list_presets()
    except Exception as exc:  # pragma: no cover - packaging error
        raise typer.BadParameter(str(exc)) from exc
    if preset not in known:
        raise typer.BadParameter(f"Unknown preset {preset!r}. Choose one of: {', '.join(known)}")
    return preset


def _output_path(source: Path, root: Path, out: Path | None) -> Path:
    if out is None:
        return source
    if root.is_file():
        if out.suffix.lower() == ".md":
            return out
        return out / source.name
    relative = source.relative_to(root)
    return out / relative


@app.command()
def polish(
    path: Path = typer.Argument(..., exists=True, help="Markdown file or directory"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="Write results here instead of in place"),
    preset: str = PresetOption,
    ai: bool = AiOption,
    site_url: Optional[str] = SiteOption,
    toc: bool = TocOption,
    dry_run: bool = typer.Option(False, "--dry-run", help="Print results without writing files"),
) -> None:
    """Apply publish rules and write blog-ready Markdown."""
    preset = _validate_preset(preset)
    files = iter_markdown_files(path)
    if not files:
        typer.echo("No Markdown files found.", err=True)
        raise typer.Exit(code=1)

    options = PolishOptions(preset=preset, ai=ai, site_url=site_url, toc=toc)
    written = 0
    errors = 0
    for source in files:
        try:
            result = polish_path(source, options)
        except Exception as exc:  # noqa: BLE001 — keep a batch going after one bad file
            errors += 1
            typer.echo(f"ERROR {source}: {exc}", err=True)
            continue
        dest = _output_path(source, path, out)
        if dry_run:
            typer.echo(f"Would write {dest}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(result.markdown, encoding="utf-8")
            written += 1
            label = dest if dest != source else source
            typer.echo(f"Polished {label}")
        for warning in result.warnings:
            typer.echo(f"  warning: {warning}")
        for issue in result.issues:
            typer.echo(f"  issue: {issue}")
    if dry_run:
        typer.echo(f"Checked {len(files) - errors} file{'s' if len(files) != 1 else ''}.")
    else:
        typer.echo(f"Wrote {written} file{'s' if written != 1 else ''}.")
    if errors:
        raise typer.Exit(code=1)


@app.command()
def check(
    path: Path = typer.Argument(..., exists=True, help="Markdown file or directory"),
    preset: str = PresetOption,
    ai: bool = AiOption,
    site_url: Optional[str] = SiteOption,
    toc: bool = TocOption,
) -> None:
    """Lint files after the deterministic pipeline. Exits 1 if unpublished-ready."""
    preset = _validate_preset(preset)
    files = iter_markdown_files(path)
    if not files:
        typer.echo("No Markdown files found.", err=True)
        raise typer.Exit(code=1)

    options = PolishOptions(preset=preset, ai=ai, site_url=site_url, toc=toc)
    failed = 0
    for source in files:
        try:
            result = polish_path(source, options)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            typer.echo(f"ERROR {source}: {exc}")
            continue
        if result.issues:
            failed += 1
            typer.echo(f"FAIL {source}")
            for issue in result.issues:
                typer.echo(f"  {issue}")
        else:
            typer.echo(f"OK   {source}")
        for warning in result.warnings:
            typer.echo(f"  warning: {warning}")

    if failed:
        typer.echo(f"{failed} file{'s' if failed != 1 else ''} not publish-ready.", err=True)
        raise typer.Exit(code=1)
    typer.echo("All files are publish-ready.")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(8000, "--port", help="Bind port"),
) -> None:
    """Start the preview UI."""
    from mdpub.web.app import create_app

    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    app()
