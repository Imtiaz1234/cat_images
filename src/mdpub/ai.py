"""Optional OpenAI-compatible metadata fill for blog frontmatter."""

from __future__ import annotations

import json
import os
import re
from typing import Any

SYSTEM_PROMPT = """You write blog metadata. Reply with a single JSON object only.
Keys: title (string), description (1-2 sentences), tags (3-8 short strings), slug (kebab-case ASCII).
Do not rewrite the article. Do not add markdown. Do not wrap the JSON in fences."""


def api_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("MDPUB_API_KEY"))


def _client():
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("MDPUB_API_KEY") or "unused"
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("MDPUB_BASE_URL")
    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response was not JSON")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("Model JSON must be an object")
    return data


def generate_metadata(
    *,
    title: str | None,
    body: str,
    missing: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    """Ask the model for missing metadata fields. Returns only requested keys."""
    if not missing:
        return {}
    excerpt = body.strip()
    if len(excerpt) > 2000:
        excerpt = excerpt[:2000].rsplit("\n", 1)[0] + "\n…"
    user = {
        "missing_fields": missing,
        "title": title,
        "markdown_excerpt": excerpt,
    }
    client = _client()
    chosen = model or os.environ.get("OPENAI_MODEL") or os.environ.get("MDPUB_MODEL") or "gpt-4o-mini"
    response = client.chat.completions.create(
        model=chosen,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content or ""
    data = _parse_json(content)

    cleaned: dict[str, Any] = {}
    if "title" in missing and isinstance(data.get("title"), str) and data["title"].strip():
        cleaned["title"] = data["title"].strip()
    if "description" in missing and isinstance(data.get("description"), str) and data["description"].strip():
        cleaned["description"] = data["description"].strip()
    if "slug" in missing and isinstance(data.get("slug"), str) and data["slug"].strip():
        cleaned["slug"] = data["slug"].strip()
    if "tags" in missing:
        tags = data.get("tags")
        if isinstance(tags, list):
            cleaned["tags"] = [str(tag).strip() for tag in tags if str(tag).strip()]
        elif isinstance(tags, str) and tags.strip():
            cleaned["tags"] = [part.strip() for part in tags.split(",") if part.strip()]
    return cleaned
