from datetime import datetime
from pathlib import Path

from typer.testing import CliRunner

from mdpub.cli import app
from mdpub.pipeline import PolishOptions, polish_text

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures"


def test_polish_writes_out_directory(tmp_path: Path):
    dest = tmp_path / "out"
    result = runner.invoke(
        app,
        ["polish", str(FIXTURES / "messy.md"), "--out", str(dest), "--site-url", "https://ex.com"],
    )
    assert result.exit_code == 0, result.output
    written = dest / "messy.md"
    assert written.exists()
    text = written.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "title:" in text


def test_polish_directory_preserves_relative_paths(tmp_path: Path):
    src = tmp_path / "posts" / "nested"
    src.mkdir(parents=True)
    (src / "a.md").write_text("# Hello\n\nWorld.\n", encoding="utf-8")
    out = tmp_path / "dist"
    result = runner.invoke(app, ["polish", str(tmp_path / "posts"), "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "nested" / "a.md").exists()


def test_check_fails_on_empty_and_passes_complete(tmp_path: Path):
    failed = runner.invoke(app, ["check", str(FIXTURES / "empty.md")])
    assert failed.exit_code == 1
    assert "FAIL" in failed.output

    complete = tmp_path / "ok.md"
    polished = polish_text(
        """---
title: Ready
description: A complete post.
tags: [garden]
---

# Ready

Enough body text to keep.
""",
        PolishOptions(now=datetime(2026, 9, 1)),
    )
    complete.write_text(polished.markdown, encoding="utf-8")
    ok = runner.invoke(app, ["check", str(complete)])
    assert ok.exit_code == 0, ok.output
    assert "publish-ready" in ok.output


def test_cli_rejects_unknown_preset():
    result = runner.invoke(app, ["check", str(FIXTURES / "messy.md"), "--preset", "nope"])
    assert result.exit_code != 0
