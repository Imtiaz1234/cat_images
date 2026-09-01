# mdpub

Polish messy Markdown into **blog-ready, publishable** posts.

`mdpub` applies a deterministic rules pipeline (headings, images, YAML frontmatter, slugs, canonical URLs) and can optionally ask an OpenAI-compatible model to fill missing title, description, tags, and slug. It does **not** rewrite the article body.

## Install

```bash
python3 -m pip install -e ".[dev]"
```

Requires Python 3.12+.

## CLI

```bash
# Clean a file or an entire folder (writes in place)
mdpub polish PATH [--out DIR] [--preset hugo|jekyll|astro|generic] [--ai] [--site-url URL] [--toc] [--dry-run]

# Lint only — exit 1 if required frontmatter is still missing
mdpub check PATH [--preset ...]

# Side-by-side preview UI
mdpub serve [--host 127.0.0.1] [--port 8000]
```

Directory mode walks `*.md` recursively. `--out` preserves relative paths.

## Presets

| Preset    | Date key  | Slug key    | Canonical key   |
|-----------|-----------|-------------|-----------------|
| generic   | `date`    | `slug`      | `canonical`     |
| hugo      | `date`    | `slug`      | `canonicalURL`  |
| jekyll    | `date`    | `permalink` | `canonical_url` |
| astro     | `pubDate` | `slug`      | `canonical`     |

Required fields after polish: title, description, date, tags, slug. Date, slug, draft, description (first paragraph), and tags (from title/headings) are filled deterministically. `--ai` can replace those guesses with model-written metadata.

## AI metadata

Set an OpenAI-compatible key. Local servers such as Ollama work via `OPENAI_BASE_URL`.

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1   # optional
export OPENAI_MODEL=gpt-4o-mini                    # optional

mdpub polish ./posts --ai --site-url https://example.com
```

Without a key, `--ai` is skipped and `check` reports remaining gaps.

## Web UI

```bash
mdpub serve --host 0.0.0.0 --port 8000
```

Open `/` to paste or upload Markdown, pick a preset, preview the polished source and rendered HTML, then download the result.

`POST /api/polish` accepts:

```json
{ "markdown": "# Draft", "preset": "hugo", "ai": false, "site_url": "https://example.com", "toc": false }
```

## Rules

Configured in [`src/mdpub/rules/default.yaml`](src/mdpub/rules/default.yaml):

- One H1; extra H1s are demoted; a missing H1 is taken from the title or the first heading
- No skipped heading levels
- Empty image alts are filled from the filename (Markdown, reference-style, and HTML `<img>`)
- Invalid YAML frontmatter is skipped instead of crashing the batch or API
- Existing Jekyll permalinks keep their directory prefix
- Unicode titles fall back to the filename (then `untitled`) for the slug
- Tags inferred from title and headings when missing
- Consistent Markdown via [mdformat](https://mdformat.readthedocs.io/)
- ISO dates, kebab-case slugs, optional TOC, canonical URL from `--site-url`

## Tests

```bash
python3 -m pytest
```

## License

MIT. See [LICENSE](LICENSE).
