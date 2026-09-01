"""Load publish rules and frontmatter presets from YAML."""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from typing import Any

import yaml
from pydantic import BaseModel, Field


class HeadingRules(BaseModel):
    require_single_h1: bool = True
    no_skipped_levels: bool = True


class ImageRules(BaseModel):
    require_alt: bool = True


class CanonicalRules(BaseModel):
    trailing_slash: bool = True


class PresetConfig(BaseModel):
    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)
    keys: dict[str, str] = Field(default_factory=dict)


class RulesConfig(BaseModel):
    toc: bool = False
    headings: HeadingRules = Field(default_factory=HeadingRules)
    images: ImageRules = Field(default_factory=ImageRules)
    canonical: CanonicalRules = Field(default_factory=CanonicalRules)
    presets: dict[str, PresetConfig] = Field(default_factory=dict)


@lru_cache(maxsize=1)
def load_rules() -> RulesConfig:
    path = resources.files("mdpub.rules").joinpath("default.yaml")
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RulesConfig.model_validate(data)


def list_presets() -> list[str]:
    return sorted(load_rules().presets)


def get_preset(name: str) -> PresetConfig:
    rules = load_rules()
    key = name.lower().strip()
    if key not in rules.presets:
        known = ", ".join(list_presets())
        raise ValueError(f"Unknown preset {name!r}. Choose one of: {known}")
    return rules.presets[key]
