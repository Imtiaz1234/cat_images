"""Parse → rules → optional AI → validate → serialize."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from mdpub.config import RulesConfig, get_preset, load_rules
from mdpub.frontmatter_util import (
    get_logical,
    is_missing,
    key_for,
    ordered_frontmatter,
    set_logical,
    write_slug,
)
from mdpub.rules_engine import (
    apply_body_rules,
    apply_frontmatter_rules,
    first_paragraph_excerpt,
    infer_tags,
    slugify,
)


@dataclass
class PolishOptions:
    preset: str = "generic"
    ai: bool = False
    site_url: str | None = None
    toc: bool | None = None
    source_name: str | None = None
    now: datetime | None = None


@dataclass
class PolishResult:
    markdown: str
    frontmatter: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    body: str = ""


def _dump_markdown(meta: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(
        meta,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip()
    body = body.lstrip("\n")
    if not body.endswith("\n"):
        body += "\n"
    return f"---\n{dumped}\n---\n\n{body}"


def _missing_logical_fields(meta: dict[str, Any], preset) -> list[str]:
    missing: list[str] = []
    for logical in ("title", "description", "tags", "slug"):
        if is_missing(get_logical(meta, preset, logical)):
            missing.append(logical)
    return missing


def _collect_issues(meta: dict[str, Any], preset) -> list[str]:
    issues: list[str] = []
    for logical in preset.required:
        value = get_logical(meta, preset, logical)
        if is_missing(value):
            issues.append(f"Missing required field: {key_for(preset, logical)}")
    return issues


def polish_text(markdown: str, options: PolishOptions | None = None) -> PolishResult:
    options = options or PolishOptions()
    rules: RulesConfig = load_rules()
    preset = get_preset(options.preset)
    warnings: list[str] = []
    now = options.now or datetime.now()
    today: date = now.date() if isinstance(now, datetime) else now
    site_url = (options.site_url or "").strip() or None
    options = PolishOptions(
        preset=options.preset,
        ai=options.ai,
        site_url=site_url,
        toc=options.toc,
        source_name=options.source_name,
        now=options.now,
    )

    meta, body, parse_warnings = _parse_document(markdown)
    warnings.extend(parse_warnings)
    toc = rules.toc if options.toc is None else options.toc

    existing_title = get_logical(meta, preset, "title")
    title_hint = str(existing_title).strip() if not is_missing(existing_title) else None

    body, inferred_title, body_warnings = apply_body_rules(
        body,
        title=title_hint,
        rules=rules,
        toc=toc,
    )
    warnings.extend(body_warnings)
    title = title_hint or inferred_title

    slug_hint = None
    if options.source_name:
        slug_hint = Path(options.source_name).stem

    meta, title, slug, fm_warnings = apply_frontmatter_rules(
        meta,
        preset=preset,
        rules=rules,
        title=title,
        slug_hint=slug_hint,
        site_url=options.site_url,
        today=today,
        source_name=options.source_name,
    )
    warnings.extend(fm_warnings)

    if options.ai:
        from mdpub.ai import api_configured, generate_metadata

        missing = _missing_logical_fields(meta, preset)
        if missing and not api_configured():
            warnings.append("AI requested but no OPENAI_API_KEY is set; skipped AI metadata")
        elif missing:
            try:
                generated = generate_metadata(title=title, body=body, missing=missing)
                if "title" in generated and is_missing(get_logical(meta, preset, "title")):
                    title = generated["title"]
                    set_logical(meta, preset, "title", title)
                    if inferred_title is None and title:
                        body = f"# {title}\n\n{body.lstrip()}"
                        warnings.append("Inserted H1 from AI title")
                if "description" in generated:
                    set_logical(meta, preset, "description", generated["description"])
                if "tags" in generated:
                    set_logical(meta, preset, "tags", generated["tags"])
                if "slug" in generated:
                    slug = slugify(generated["slug"])
                    set_logical(meta, preset, "slug", write_slug(slug, preset))
                    if options.site_url and is_missing(get_logical(meta, preset, "canonical")):
                        url = f"{options.site_url.rstrip('/')}/{slug.strip('/')}"
                        if rules.canonical.trailing_slash:
                            url += "/"
                        set_logical(meta, preset, "canonical", url)
            except Exception as exc:  # noqa: BLE001 — surface model/network failures as warnings
                warnings.append(f"AI metadata failed: {exc}")

    if is_missing(get_logical(meta, preset, "description")):
        excerpt = first_paragraph_excerpt(body)
        if excerpt:
            set_logical(meta, preset, "description", excerpt)
            warnings.append("Filled description from first paragraph")
    if is_missing(get_logical(meta, preset, "tags")):
        tags = infer_tags(title, body)
        if tags:
            set_logical(meta, preset, "tags", tags)
            warnings.append("Inferred tags from title and headings")

    if title and is_missing(get_logical(meta, preset, "title")):
        set_logical(meta, preset, "title", title)

    ordered = ordered_frontmatter(meta, preset)
    issues = _collect_issues(ordered, preset)
    rendered = _dump_markdown(ordered, body)
    return PolishResult(
        markdown=rendered,
        frontmatter=ordered,
        warnings=warnings,
        issues=issues,
        body=body,
    )


def _short_error(exc: Exception) -> str:
    text = str(exc).strip().splitlines()[0]
    return text or type(exc).__name__


def _recover_body(markdown: str) -> str:
    if markdown.startswith("---"):
        parts = markdown.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return markdown


def _parse_document(markdown: str) -> tuple[dict[str, Any], str, list[str]]:
    try:
        post = frontmatter.loads(markdown)
        return dict(post.metadata), post.content or "", []
    except Exception as exc:
        body = _recover_body(markdown)
        return {}, body, [f"Ignored invalid frontmatter ({_short_error(exc)}); treating file as body-only"]


def polish_path(path: Path, options: PolishOptions | None = None) -> PolishResult:
    options = options or PolishOptions()
    if not options.source_name:
        options = PolishOptions(
            preset=options.preset,
            ai=options.ai,
            site_url=options.site_url,
            toc=options.toc,
            source_name=path.name,
            now=options.now,
        )
    text = path.read_text(encoding="utf-8")
    return polish_text(text, options)


def iter_markdown_files(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() != ".md":
            raise ValueError(f"Not a Markdown file: {path}")
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*.md") if p.is_file())
    raise FileNotFoundError(f"Path not found: {path}")
