from datetime import datetime
from pathlib import Path

import pytest

from mdpub.config import get_preset
from mdpub.frontmatter_util import get_logical
from mdpub.pipeline import PolishOptions, polish_path, polish_text

NOW = datetime(2026, 9, 1, 12, 0, 0)
FIXTURES = Path(__file__).parent / "fixtures"


def test_messy_fixture_becomes_publishable_minus_tags():
    source = (FIXTURES / "messy.md").read_text(encoding="utf-8")
    result = polish_text(
        source,
        PolishOptions(preset="generic", site_url="https://example.com", now=NOW),
    )
    meta = result.frontmatter
    assert meta["title"] == "Getting started with backyard compost"
    assert meta["date"].isoformat() == "2026-09-01"
    assert meta["slug"] == "getting-started-with-backyard-compost"
    assert meta["canonical"] == "https://example.com/getting-started-with-backyard-compost/"
    assert meta["draft"] is False
    assert "Kitchen scraps" in meta["description"]
    assert result.markdown.startswith("---\n")
    assert result.markdown.count("# Getting started with backyard compost") == 1
    assert "## Why it matters" in result.markdown
    assert "### Common mistakes" in result.markdown
    assert "![bin setup](bin-setup.png)" in result.markdown
    assert "- bucket" in result.markdown
    assert "- pitchfork" in result.markdown
    assert any("Missing required field: tags" in issue for issue in result.issues)


def test_presets_use_expected_keys():
    source = (FIXTURES / "messy.md").read_text(encoding="utf-8")
    hugo = polish_text(source, PolishOptions(preset="hugo", site_url="https://ex.com", now=NOW))
    assert "canonicalURL" in hugo.frontmatter
    assert "canonical" not in hugo.frontmatter

    jekyll = polish_text(source, PolishOptions(preset="jekyll", now=NOW))
    assert jekyll.frontmatter["permalink"] == "/getting-started-with-backyard-compost/"

    astro = polish_text(source, PolishOptions(preset="astro", now=NOW))
    assert "pubDate" in astro.frontmatter
    assert astro.frontmatter["pubDate"].isoformat() == "2026-09-01"


def test_check_fails_when_title_cannot_be_inferred():
    source = (FIXTURES / "empty.md").read_text(encoding="utf-8")
    result = polish_text(source, PolishOptions(now=NOW))
    assert any("title" in issue for issue in result.issues)


def test_keeps_existing_frontmatter():
    markdown = """---
title: Kept Title
description: Kept description
date: 2020-01-02
tags:
  - soil
slug: kept-slug
---

# Kept Title

Body paragraph.
"""
    result = polish_text(markdown, PolishOptions(now=NOW, site_url="https://ex.com"))
    assert result.frontmatter["title"] == "Kept Title"
    assert result.frontmatter["description"] == "Kept description"
    assert result.frontmatter["date"].isoformat() == "2020-01-02"
    assert result.frontmatter["tags"] == ["soil"]
    assert result.frontmatter["slug"] == "kept-slug"
    assert result.issues == []


def test_unknown_preset_raises():
    with pytest.raises(ValueError, match="Unknown preset"):
        get_preset("wordpress")


def test_polish_path_uses_filename_slug():
    result = polish_path(
        FIXTURES / "empty.md",
        PolishOptions(now=NOW),
    )
    assert result.frontmatter.get("slug") == "empty"


def test_toc_option_inserts_headings():
    source = (FIXTURES / "messy.md").read_text(encoding="utf-8")
    result = polish_text(source, PolishOptions(toc=True, now=NOW))
    assert "Table of Contents" in result.markdown
    assert get_logical(result.frontmatter, get_preset("generic"), "title")
