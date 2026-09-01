"""Deterministic Markdown cleanup for publishable blog posts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import mdformat

from mdpub.config import RulesConfig
from mdpub.frontmatter_util import (
    get_logical,
    is_missing,
    normalize_date,
    normalize_tags,
    read_slug,
    set_logical,
    write_slug,
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
SETEXT_H1_RE = re.compile(r"^=+\s*$")
SETEXT_H2_RE = re.compile(r"^-{3,}\s*$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\)")
FENCE_RE = re.compile(r"^(```|~~~)")
TOC_HEADING_RE = re.compile(r"^#{2,6}\s+table of contents\s*$", re.IGNORECASE)
REF_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\[([^\]]+)\]")
LINK_DEF_RE = re.compile(r"^\[([^\]]+)\]:\s+(\S+)")
HTML_IMG_RE = re.compile(r"<img\b([^>]*?)(/?)>", re.IGNORECASE | re.DOTALL)
HTML_SRC_RE = re.compile(r"""\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
HTML_ALT_RE = re.compile(r"""\balt\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
EMPTY_LINK_RE = re.compile(r"\[[^\]]+\]\(\s*\)")
STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "for",
        "to",
        "of",
        "in",
        "on",
        "it",
        "is",
        "are",
        "was",
        "be",
        "this",
        "that",
        "with",
        "from",
        "how",
        "why",
        "what",
        "when",
        "your",
        "you",
        "our",
        "getting",
        "started",
        "common",
        "only",
        "just",
        "about",
        "into",
        "using",
        "use",
        "into",
        "its",
        "not",
        "but",
        "can",
        "will",
        "more",
        "than",
        "then",
    }
)


@dataclass
class EngineResult:
    body: str
    meta: dict
    warnings: list[str] = field(default_factory=list)
    title: str | None = None
    slug: str | None = None


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", "-", ascii_text)
    return ascii_text.strip("-")


def _is_fence(line: str) -> bool:
    return bool(FENCE_RE.match(line.strip()))


def _iter_line_state(lines: list[str]):
    in_fence = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if _is_fence(stripped):
            in_fence = not in_fence
            yield index, line, True
            continue
        yield index, line, in_fence


def convert_setext_headings(body: str) -> str:
    lines = body.splitlines()
    out: list[str] = []
    in_fence = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if _is_fence(stripped):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if (
            not in_fence
            and i + 1 < len(lines)
            and stripped
            and not stripped.startswith("#")
        ):
            underline = lines[i + 1].strip()
            if SETEXT_H1_RE.match(underline):
                out.append(f"# {stripped}")
                i += 2
                continue
            if SETEXT_H2_RE.match(underline):
                out.append(f"## {stripped}")
                i += 2
                continue
        out.append(line)
        i += 1
    return "\n".join(out)


def normalize_whitespace(body: str) -> str:
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+$", "", line) for line in body.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def extract_headings(body: str) -> list[tuple[int, int, str]]:
    """Return (line_index, level, text) for ATX headings outside fences."""
    found: list[tuple[int, int, str]] = []
    for index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            found.append((index, len(match.group(1)), match.group(2).strip()))
    return found


def _replace_heading_line(line: str, level: int, text: str) -> str:
    return f"{'#' * level} {text}"


def ensure_single_h1(
    body: str,
    title: str | None,
    require_single_h1: bool,
) -> tuple[str, str | None, list[str]]:
    if not require_single_h1:
        headings = extract_headings(body)
        inferred = title
        for _, level, text in headings:
            if level == 1:
                inferred = inferred or text
                break
        if inferred is None and headings:
            inferred = headings[0][2]
        return body, inferred, []

    warnings: list[str] = []
    lines = body.splitlines()
    headings = extract_headings(body)
    h1s = [(idx, text) for idx, level, text in headings if level == 1]

    inferred = title
    if h1s:
        inferred = inferred or h1s[0][1]
        if len(h1s) > 1:
            for idx, _text in h1s[1:]:
                match = HEADING_RE.match(lines[idx])
                if match:
                    lines[idx] = _replace_heading_line(lines[idx], 2, match.group(2).strip())
            warnings.append("Demoted extra H1 headings to H2")
    elif inferred:
        lines.insert(0, f"# {inferred}")
        if len(lines) > 1 and lines[1].strip():
            lines.insert(1, "")
        warnings.append("Inserted H1 from title")
    elif headings:
        idx, _level, text = headings[0]
        match = HEADING_RE.match(lines[idx])
        if match:
            lines[idx] = _replace_heading_line(lines[idx], 1, match.group(2).strip())
        inferred = text
        warnings.append("Promoted first heading to H1")
    else:
        warnings.append("Could not infer title; no H1 present")

    return "\n".join(lines) + ("\n" if lines else ""), inferred, warnings


def fix_skipped_heading_levels(body: str) -> tuple[str, list[str]]:
    lines = body.splitlines()
    last_level = 0
    changed = False
    for index, line, in_fence in _iter_line_state(lines):
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        text = match.group(2).strip()
        target = level
        if last_level and level > last_level + 1:
            target = last_level + 1
        elif last_level == 0 and level > 1:
            target = 1
        if target != level:
            lines[index] = _replace_heading_line(line, target, text)
            changed = True
            level = target
        last_level = level
    warning = ["Normalized skipped heading levels"] if changed else []
    return "\n".join(lines) + ("\n" if lines else ""), warning


def fill_image_alts(body: str) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        alt, url = match.group(1), match.group(2)
        if alt.strip():
            return match.group(0)
        name = Path(unquote(urlparse(url).path)).stem
        name = name.replace("-", " ").replace("_", " ").strip() or "image"
        warnings.append(f"Filled image alt from filename: {name}")
        closer = match.group(0).index("](")
        return f"![{name}{match.group(0)[closer:]}"

    # Only rewrite images outside fences.
    out_lines: list[str] = []
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            out_lines.append(line)
        else:
            out_lines.append(IMAGE_RE.sub(replacer, line))
    return "\n".join(out_lines) + ("\n" if out_lines else ""), warnings


def _alt_from_url(url: str) -> str:
    name = Path(unquote(urlparse(url).path)).stem
    name = name.replace("-", " ").replace("_", " ").strip()
    return name or "image"


def fill_reference_image_alts(body: str) -> tuple[str, list[str]]:
    defs: dict[str, str] = {}
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            continue
        match = LINK_DEF_RE.match(line.strip())
        if match:
            defs[match.group(1).strip().lower()] = match.group(2)
    warnings: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        alt, ident = match.group(1), match.group(2)
        if alt.strip():
            return match.group(0)
        url = defs.get(ident.strip().lower(), ident)
        name = _alt_from_url(url)
        warnings.append(f"Filled image alt from filename: {name}")
        return f"![{name}][{ident}]"

    out: list[str] = []
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            out.append(line)
        else:
            out.append(REF_IMAGE_RE.sub(replacer, line))
    return "\n".join(out) + ("\n" if out else ""), warnings


def fill_html_image_alts(body: str) -> tuple[str, list[str]]:
    warnings: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        attrs, closer = match.group(1), match.group(2)
        alt_match = HTML_ALT_RE.search(attrs)
        if alt_match and alt_match.group(1).strip():
            return match.group(0)
        src_match = HTML_SRC_RE.search(attrs)
        if not src_match:
            return match.group(0)
        name = _alt_from_url(src_match.group(1))
        if alt_match:
            attrs = HTML_ALT_RE.sub(f'alt="{name}"', attrs, count=1)
        else:
            attrs = attrs.rstrip() + f' alt="{name}"'
        warnings.append(f"Filled image alt from filename: {name}")
        return f"<img{attrs}{closer}>"

    out: list[str] = []
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            out.append(line)
        else:
            out.append(HTML_IMG_RE.sub(replacer, line))
    return "\n".join(out) + ("\n" if out else ""), warnings


def warn_empty_links(body: str) -> list[str]:
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if not in_fence and EMPTY_LINK_RE.search(line):
            return ["Empty link destination found"]
    return []


def infer_tags(title: str | None, body: str, limit: int = 8) -> list[str]:
    texts: list[str] = []
    if title:
        texts.append(title)
    for _idx, _level, text in extract_headings(body):
        if TOC_HEADING_RE.match("#" * _level + " " + text):
            continue
        texts.append(text)
    tags: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", text):
            lowered = word.lower()
            if lowered in STOPWORDS or lowered in seen:
                continue
            seen.add(lowered)
            tags.append(lowered)
            if len(tags) >= limit:
                return tags
    return tags


LIST_MARKER_RE = re.compile(r"^(\s*)[*+](\s+)")


def normalize_list_markers(body: str) -> str:
    out: list[str] = []
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            out.append(line)
        else:
            out.append(LIST_MARKER_RE.sub(r"\1-\2", line))
    return "\n".join(out) + ("\n" if out else "")


def format_markdown(body: str) -> str:
    try:
        formatted = mdformat.text(body, options={"wrap": "keep"})
    except Exception:
        formatted = body
    return formatted if formatted.endswith("\n") else formatted + "\n"


def _toc_items(body: str) -> list[tuple[int, str]]:
    items: list[tuple[int, str]] = []
    for _idx, level, text in extract_headings(body):
        if TOC_HEADING_RE.match("#" * level + " " + text):
            continue
        if level == 1:
            continue
        items.append((level, text))
    return items


def insert_toc(body: str) -> tuple[str, list[str]]:
    items = _toc_items(body)
    if not items:
        return body, []

    lines = body.splitlines()
    existing = False
    for index, line, in_fence in _iter_line_state(lines):
        if in_fence:
            continue
        if TOC_HEADING_RE.match(line.strip()):
            existing = True
            break
    if existing:
        return body, []

    toc_lines = ["## Table of Contents", ""]
    min_level = min(level for level, _text in items)
    for level, text in items:
        indent = "  " * (level - min_level)
        toc_lines.append(f"{indent}- [{text}](#{slugify(text)})")
    toc_lines.append("")

    insert_at = 0
    headings = extract_headings(body)
    if headings and headings[0][1] == 1:
        insert_at = headings[0][0] + 1
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1
    new_lines = lines[:insert_at] + [""] + toc_lines + lines[insert_at:]
    return "\n".join(new_lines) + "\n", ["Inserted table of contents"]


def first_paragraph_excerpt(body: str, limit: int = 200) -> str | None:
    chunks: list[str] = []
    for _index, line, in_fence in _iter_line_state(body.splitlines()):
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped:
            if chunks:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("!") or stripped.startswith(">"):
            continue
        if stripped.startswith("|") or stripped.startswith("- ") or stripped.startswith("* "):
            continue
        if stripped.startswith("```"):
            continue
        chunks.append(stripped)
    if not chunks:
        return None
    text = " ".join(chunks)
    text = re.sub(r"[*_`]+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        trimmed = text[: limit - 1].rsplit(" ", 1)[0]
        text = (trimmed or text[: limit - 1]).rstrip(".,;:") + "…"
    return text or None


def apply_body_rules(
    body: str,
    *,
    title: str | None,
    rules: RulesConfig,
    toc: bool,
) -> tuple[str, str | None, list[str]]:
    warnings: list[str] = []
    body = convert_setext_headings(body)
    body = normalize_whitespace(body)
    body, inferred, extra = ensure_single_h1(body, title, rules.headings.require_single_h1)
    warnings.extend(extra)
    if rules.headings.no_skipped_levels:
        body, extra = fix_skipped_heading_levels(body)
        warnings.extend(extra)
    if rules.images.require_alt:
        body, extra = fill_image_alts(body)
        warnings.extend(extra)
        body, extra = fill_reference_image_alts(body)
        warnings.extend(extra)
        body, extra = fill_html_image_alts(body)
        warnings.extend(extra)
    warnings.extend(warn_empty_links(body))
    body = normalize_list_markers(body)
    body = format_markdown(body)
    if toc:
        body, extra = insert_toc(body)
        warnings.extend(extra)
        body = format_markdown(body)
    return body, inferred, warnings


def apply_frontmatter_rules(
    meta: dict,
    *,
    preset,
    rules: RulesConfig,
    title: str | None,
    slug_hint: str | None,
    site_url: str | None,
    today: date,
    source_name: str | None,
) -> tuple[dict, str | None, str | None, list[str]]:
    warnings: list[str] = []
    meta = dict(meta)

    current_title = get_logical(meta, preset, "title")
    if is_missing(current_title) and title:
        set_logical(meta, preset, "title", title)
        current_title = title
    elif not is_missing(current_title):
        current_title = str(current_title).strip()

    current_date = normalize_date(get_logical(meta, preset, "date"), today)
    set_logical(meta, preset, "date", current_date)

    tags = normalize_tags(get_logical(meta, preset, "tags"))
    if tags:
        set_logical(meta, preset, "tags", tags)

    existing_slug_field = get_logical(meta, preset, "slug")
    if is_missing(existing_slug_field):
        candidates: list[str] = []
        if current_title:
            candidates.append(slugify(str(current_title)))
        if slug_hint:
            candidates.append(slugify(str(slug_hint)))
        if source_name:
            candidates.append(slugify(Path(source_name).stem))
        slug = next((item for item in candidates if item), "untitled")
        set_logical(meta, preset, "slug", write_slug(slug, preset))
    else:
        slug = read_slug(meta, preset)

    if is_missing(get_logical(meta, preset, "draft")):
        set_logical(meta, preset, "draft", False)

    if is_missing(get_logical(meta, preset, "canonical")) and site_url and slug:
        base = site_url.rstrip("/")
        path = slug.strip("/")
        url = f"{base}/{path}"
        if rules.canonical.trailing_slash:
            url += "/"
        set_logical(meta, preset, "canonical", url)

    description = get_logical(meta, preset, "description")
    if is_missing(description):
        # Leave empty for AI; deterministic excerpt is applied by the pipeline
        # only as a last-resort warning, not here.
        pass

    return meta, (str(current_title) if current_title else None), slug, warnings
