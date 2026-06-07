"""InfographicRenderer — renders a single infographic card to PNG.

Renderer: Jinja2 template + Playwright screenshot. No LLM calls.
All intelligence (content structure, layout selection) happens upstream.
"""

import base64
import json
import os
import time
from pathlib import Path

import requests
from groq import Groq
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

from services.style_service import StyleService

_HF_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

_IMAGE_PROMPT_TEMPLATE = """Generate a short image prompt for FLUX image generator.
The image will be embedded inside a dark navy infographic card about this topic:

{concept}

Requirements:
- Abstract, minimal, technical aesthetic
- Dark compatible — will sit on #060b18 dark background
- No text, no letters, no words
- Geometric, network, or flowing abstract shapes
- Colors: electric blue, cyan, deep navy
- Style: clean digital art, minimal

Return ONLY the prompt. Max 40 words."""

_PLATFORM_DIMENSIONS: dict[str, tuple[int, int]] = {
    "linkedin":           (1080, 1080),
    "linkedin_landscape": (1200, 627),
    "linkedin_portrait":  (1080, 1350),
    "instagram":          (1080, 1080),
    "instagram_portrait": (1080, 1350),
    "default":            (1080, 1080),
}


class InfographicRenderer:

    def __init__(
        self,
        templates_dir: str = "templates",
        output_dir: str = "data/images",
    ) -> None:
        self._groq = Groq()
        self._templates_dir = Path(templates_dir).resolve()
        self._env = Environment(loader=FileSystemLoader(str(self._templates_dir)))
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def render_direct(
        self,
        template_type: str,
        card_data: dict,
        platform: str = "default",
        style: str = "linear_dark",
    ) -> str:
        """Render from pre-structured card data. Returns PNG path."""
        print(f"  Template: {template_type}  Platform: {platform}  Style: {style}")
        data = dict(card_data)
        data["type"] = template_type

        concept = (
            data.get("concept_name") or data.get("system_name") or
            data.get("headline") or data.get("project") or "AI agents"
        )
        illustration = self._generate_illustration(concept)
        if illustration:
            data["illustration"] = illustration

        html = self._render(template_type, data, platform, style)
        return self._screenshot(html, template_type, platform)

    def generate(
        self,
        post_text: str,
        platform: str = "default",
        style: str = "linear_dark",
    ) -> str:
        """Legacy: extract structure from post text, then render."""
        data = self._extract_structure(post_text)
        return self.render_direct(
            data.get("type", "concept_card"), data,
            platform=platform, style=style,
        )

    # ── Internal ────────────────────────────────────────────────────────────

    def _render(
        self,
        template_type: str,
        data: dict,
        platform: str = "default",
        style: str = "linear_dark",
    ) -> str:
        ss = StyleService()
        w, h = _PLATFORM_DIMENSIONS.get(platform, _PLATFORM_DIMENSIONS["default"])
        base_css_url = (self._templates_dir / "_base.css").as_uri()

        extra: dict = {}
        if template_type == "architecture_card_v2":
            from renderers.svg_layout import compute_layout
            positions, phase_labels, col_w, svg_h = compute_layout(
                data.get("nodes", []),
                data.get("phases", []),
                w, h,
            )
            extra = {
                "positions":    positions,
                "phase_labels": phase_labels,
                "col_w":        col_w,
                "svg_h":        svg_h,
            }
        elif template_type == "cheat_sheet_v2":
            sections = data.get("sections") or []
            cleaned  = [{"name": s.get("name", ""), "items": s.get("items") or []}
                        for s in sections]
            extra = {
                "sections":    cleaned,
                "footer_note": data.get("footer_note", ""),
            }
            data = {k: v for k, v in data.items() if k not in ("sections", "footer_note")}

        template = self._env.get_template(f"{template_type}/template.html")
        return template.render(
            base_css_url=base_css_url,
            canvas_w=w, canvas_h=h,
            style_css=ss.css_overrides(style),
            body_class=ss.body_class(style),
            **extra,
            **data,
        )

    def _screenshot(self, html: str, label: str = "card", platform: str = "default") -> str:
        w, h = _PLATFORM_DIMENSIONS.get(platform, _PLATFORM_DIMENSIONS["default"])
        out_path = self._output_dir / f"{label}_{int(time.time())}.png"
        tmp = self._output_dir / f"_tmp_{label}.html"
        tmp.write_text(html, encoding="utf-8")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(
                    viewport={"width": w, "height": h},
                    device_scale_factor=3,
                )
                page.goto(tmp.resolve().as_uri(), wait_until="networkidle")
                page.wait_for_timeout(2000)
                page.screenshot(
                    path=str(out_path),
                    clip={"x": 0, "y": 0, "width": w, "height": h},
                    type="png",
                )
                browser.close()
        finally:
            tmp.unlink(missing_ok=True)
        return str(out_path)

    def _generate_illustration(self, concept: str) -> str | None:
        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            return None
        try:
            prompt_resp = self._groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": _IMAGE_PROMPT_TEMPLATE.format(concept=concept)}],
            )
            prompt = prompt_resp.choices[0].message.content.strip()
            print(f"  Illustration prompt: {prompt[:60]}...")

            resp = requests.post(
                _HF_URL,
                headers={"Authorization": f"Bearer {hf_token}"},
                json={"inputs": prompt, "parameters": {"width": 512, "height": 512}},
                timeout=60,
            )
            if resp.status_code == 503:
                import time as _t; _t.sleep(15)
                resp = requests.post(
                    _HF_URL,
                    headers={"Authorization": f"Bearer {hf_token}"},
                    json={"inputs": prompt, "parameters": {"width": 512, "height": 512}},
                    timeout=60,
                )
            if resp.status_code == 200:
                b64 = base64.b64encode(resp.content).decode()
                return f"data:image/jpeg;base64,{b64}"
        except Exception as e:
            print(f"  Illustration skipped: {e.__class__.__name__}")
        return None

    def _extract_structure(self, post_text: str) -> dict:
        from agents.information_architect import InformationArchitectAgent
        # Legacy path — prefer render_direct with pre-structured data
        response = self._groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": post_text}],
        )
        data = json.loads(response.choices[0].message.content)
        return self._strip_markdown(data)

    def _strip_markdown(self, obj):
        if isinstance(obj, str):
            return obj.replace("**", "").replace("__", "").replace("*", "").strip()
        if isinstance(obj, dict):
            return {k: self._strip_markdown(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._strip_markdown(i) for i in obj]
        return obj
