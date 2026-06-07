"""StyleService — loads and applies visual style presets.

Pure service: no LLM calls. Reads JSON presets from styles/ and builds
CSS variable override strings for the Jinja2 render pipeline.
"""

import json
from pathlib import Path

_STYLES_DIR = Path("styles")
_DEFAULT = "linear_dark"


def load_style(name: str) -> dict:
    path = _STYLES_DIR / f"{name}.json"
    if not path.exists():
        path = _STYLES_DIR / f"{_DEFAULT}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def list_styles() -> list[str]:
    return sorted(p.stem for p in _STYLES_DIR.glob("*.json"))


class StyleService:

    def css_overrides(self, style: str = _DEFAULT) -> str:
        """Build the :root CSS variable overrides string for this style."""
        preset = load_style(style)
        parts: list[str] = []
        for group in ("colors", "typography", "spacing"):
            for prop, value in preset.get(group, {}).items():
                parts.append(f"{prop}: {value};")
        return " ".join(parts)

    def body_class(self, style: str = _DEFAULT) -> str:
        """Optional CSS class to add to <body> for pattern backgrounds."""
        return load_style(style).get("visual", {}).get("bg_class", "")

    def illustration_opacity(self, style: str = _DEFAULT) -> str:
        return load_style(style).get("visual", {}).get("illustration_opacity", "0.07")
