"""BlockRenderer — renders a single VisualBlock to a PNG file.

Template selection is a dict lookup (block.type → template folder).
Block types without their own template fall back to block_what.
"""

from __future__ import annotations
import time
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from agents.style_agent import StyleAgent
from schemas.visual_block import VisualBlock


_TEMPLATES_DIR = Path("templates")

_BLOCK_TEMPLATE: dict[str, str] = {
    "what":       "block_what",
    "why":        "block_what",
    "inputs":     "block_what",
    "outputs":    "block_what",
    "mistakes":   "block_what",
    "flow":       "block_flow",
    "takeaway":   "block_takeaway",
    "example":    "block_what",   # fallback until block_example is built
    "comparison": "block_what",   # fallback until block_comparison is built
}

_PLATFORM_DIMENSIONS: dict[str, tuple[int, int]] = {
    "linkedin":           (1200, 1200),
    "instagram":          (1080, 1080),
    "instagram_portrait": (1080, 1350),
}


class BlockRenderer:

    def __init__(self, output_dir: str = "data/images") -> None:
        self._templates_dir = _TEMPLATES_DIR.resolve()
        self._env = Environment(loader=FileSystemLoader(str(self._templates_dir)))
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._style_agent = StyleAgent()

    def render(
        self,
        block: VisualBlock,
        platform: str = "linkedin",
        style: str = "linear_dark",
        total_slides: int = 1,
    ) -> str:
        """Render one VisualBlock to PNG. Returns the output file path."""
        template_name = _BLOCK_TEMPLATE.get(block.type, "block_what")
        html = self._render_html(block, template_name, platform, style, total_slides)
        return self._screenshot(html, block, platform)

    def render_carousel(
        self,
        blocks: list[VisualBlock],
        platform: str = "linkedin",
        style: str = "linear_dark",
    ) -> list[str]:
        """Render all blocks in a carousel. Returns list of PNG paths."""
        return [
            self.render(block, platform=platform, style=style, total_slides=len(blocks))
            for block in blocks
        ]

    # ── Internal ────────────────────────────────────────────────────────

    def _render_html(
        self,
        block: VisualBlock,
        template_name: str,
        platform: str,
        style: str,
        total_slides: int,
    ) -> str:
        w, h = _PLATFORM_DIMENSIONS.get(platform, (1200, 1200))
        base_css_url = (self._templates_dir / "_base.css").as_uri()
        template = self._env.get_template(f"{template_name}/template.html")
        slide_label = f"{block.order + 1} / {total_slides}"
        return template.render(
            base_css_url=base_css_url,
            canvas_w=w, canvas_h=h,
            style_css=self._style_agent.css_overrides(style),
            body_class=self._style_agent.body_class(style),
            slide_label=slide_label,
            block_icon=block.icon,
            **self._block_to_dict(block),
        )

    def _block_to_dict(self, block: VisualBlock) -> dict:
        return {
            "type":        block.type,
            "title":       block.title,
            "points":      block.points,
            "flow":        block.flow,
            "code":        block.code,
            "code_lang":   block.code_lang,
            "caption":     block.caption,
            "highlight":   block.highlight,
            "left":        block.left,
            "right":       block.right,
            "left_label":  block.left_label,
            "right_label": block.right_label,
            "icon":        block.icon,
            "topic":       block.topic,
        }

    def _screenshot(self, html: str, block: VisualBlock, platform: str) -> str:
        w, h = _PLATFORM_DIMENSIONS.get(platform, (1200, 1200))
        slug = f"block_{block.order:02d}_{block.type}_{int(time.time())}"
        out_path = self._output_dir / f"{slug}.png"
        tmp = self._output_dir / f"_tmp_{slug}.html"
        tmp.write_text(html, encoding="utf-8")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(
                    viewport={"width": w, "height": h},
                    device_scale_factor=3,
                )
                page.goto(tmp.resolve().as_uri(), wait_until="networkidle")
                page.wait_for_timeout(1500)
                page.screenshot(
                    path=str(out_path),
                    clip={"x": 0, "y": 0, "width": w, "height": h},
                    type="png",
                )
                browser.close()
        finally:
            tmp.unlink(missing_ok=True)
        return str(out_path)
