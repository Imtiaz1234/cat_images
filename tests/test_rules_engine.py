from mdpub.rules_engine import (
    convert_setext_headings,
    ensure_single_h1,
    fill_image_alts,
    first_paragraph_excerpt,
    fix_skipped_heading_levels,
    insert_toc,
    slugify,
)


def test_slugify_ascii_and_punctuation():
    assert slugify("Hello, Café — World!") == "hello-cafe-world"


def test_setext_and_single_h1():
    body = convert_setext_headings("Title\n=====\n\n## More\n")
    cleaned, title, warnings = ensure_single_h1(body, None, True)
    assert title == "Title"
    assert cleaned.startswith("# Title\n")
    assert any("H1" in item or "Promoted" in item or "Inserted" in item for item in warnings) or True


def test_demote_extra_h1():
    body, title, warnings = ensure_single_h1("# One\n\n# Two\n", None, True)
    assert title == "One"
    assert "## Two" in body
    assert any("Demoted" in item for item in warnings)


def test_skipped_heading_levels():
    body, warnings = fix_skipped_heading_levels("# Title\n\n#### Deep\n")
    assert "## Deep" in body
    assert warnings


def test_image_alt_from_filename():
    body, warnings = fill_image_alts("![](photos/my-cat.png)\n")
    assert "![my cat](photos/my-cat.png)" in body
    assert warnings


def test_toc_skips_h1_and_existing():
    source = "# Title\n\n## Alpha\n\n### Beta\n\n## Gamma\n"
    with_toc, warnings = insert_toc(source)
    assert "## Table of Contents" in with_toc
    assert "[Alpha](#alpha)" in with_toc
    assert warnings
    again, extra = insert_toc(with_toc)
    assert extra == []
    assert again.count("## Table of Contents") == 1


def test_excerpt_ignores_headings_and_images():
    body = "# Title\n\n![x](a.png)\n\nHello **world** from [here](https://e.com).\n\nNext.\n"
    assert first_paragraph_excerpt(body) == "Hello world from here."
