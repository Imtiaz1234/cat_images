"""FastAPI app: polish API plus static preview UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mdpub.config import list_presets
from mdpub.pipeline import PolishOptions, polish_text

STATIC_DIR = Path(__file__).resolve().parent / "static"


class PolishRequest(BaseModel):
    markdown: str
    preset: str = "generic"
    ai: bool = False
    site_url: str | None = None
    toc: bool = False


class PolishResponse(BaseModel):
    markdown: str
    frontmatter: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


def create_app() -> FastAPI:
    app = FastAPI(title="mdpub", description="Polish Markdown into publishable blog posts")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "presets": list_presets()}

    @app.post("/api/polish", response_model=PolishResponse)
    def api_polish(payload: PolishRequest) -> PolishResponse:
        try:
            result = polish_text(
                payload.markdown,
                PolishOptions(
                    preset=payload.preset,
                    ai=payload.ai,
                    site_url=payload.site_url,
                    toc=payload.toc,
                    source_name="untitled.md",
                ),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PolishResponse(
            markdown=result.markdown,
            frontmatter=result.frontmatter,
            warnings=result.warnings,
            issues=result.issues,
        )

    return app
