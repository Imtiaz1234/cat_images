"""Map logical blog fields onto preset-specific frontmatter keys."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from mdpub.config import PresetConfig


LOGICAL_FIELDS = (
    "title",
    "description",
    "date",
    "tags",
    "slug",
    "canonical",
    "draft",
)


def key_for(preset: PresetConfig, logical: str) -> str:
    return preset.keys.get(logical, logical)


def get_logical(meta: dict[str, Any], preset: PresetConfig, logical: str) -> Any:
    return meta.get(key_for(preset, logical))


def set_logical(meta: dict[str, Any], preset: PresetConfig, logical: str, value: Any) -> None:
    meta[key_for(preset, logical)] = value


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
        return True
    return False


def normalize_tags(value: Any) -> list[str]:
    if is_missing(value):
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    if isinstance(value, (list, tuple)):
        tags: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                tags.append(text)
        return tags
    return [str(value).strip()]


def normalize_date(value: Any, fallback: date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(text[:19], fmt).date()
                except ValueError:
                    continue
    return fallback


def read_slug(meta: dict[str, Any], preset: PresetConfig) -> str | None:
    raw = get_logical(meta, preset, "slug")
    if is_missing(raw):
        return None
    text = str(raw).strip()
    if key_for(preset, "slug") == "permalink":
        text = text.strip("/")
        if text.endswith(".html"):
            text = text[: -len(".html")]
        text = text.rsplit("/", 1)[-1]
    return text or None


def write_slug(slug: str, preset: PresetConfig) -> str:
    if key_for(preset, "slug") == "permalink":
        return f"/{slug.strip('/')}/"
    return slug


def ordered_frontmatter(meta: dict[str, Any], preset: PresetConfig) -> dict[str, Any]:
    """Return metadata with logical fields first, then any extras."""
    ordered: dict[str, Any] = {}
    seen: set[str] = set()
    for logical in LOGICAL_FIELDS:
        key = key_for(preset, logical)
        if key in meta:
            ordered[key] = meta[key]
            seen.add(key)
    for key, value in meta.items():
        if key not in seen:
            ordered[key] = value
    return ordered
