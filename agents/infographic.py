import base64
import json
import os
import time
from pathlib import Path

import requests
from groq import Groq
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

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


_STRUCTURE_PROMPT = """You are a content strategist. Read this LinkedIn post and extract structured data for an infographic card.

POST:
{post_text}

Choose ONE template:
- "concept_card"      — explaining what something is (ReAct, MCP, RAG, Memory, Agents) ~30%
- "architecture_card" — system design, multi-agent flows, pipelines ~25%
- "build_card"        — build-in-public progress update, day N, shipped features ~25%
- "lesson_card"       — insight, mistake, hard lesson learned ~15%
- "comparison_card"   — A vs B, old way vs new way, two approaches ~5%

Return ONLY valid JSON. No explanation. No markdown. No code block.

For concept_card:
{{
  "type": "concept_card",
  "concept_name": "SHORT NAME IN CAPS",
  "tagline": "One sentence — what it is and why it matters",
  "steps": [
    {{"label": "STEP LABEL OR EMPTY", "text": "Step Name", "desc": "optional one line description"}},
    {{"label": "", "text": "Step Name", "desc": ""}},
    {{"label": "", "text": "Step Name", "desc": ""}},
    {{"label": "", "text": "Step Name", "desc": ""}}
  ]
}}

For architecture_card:
{{
  "type": "architecture_card",
  "system_name": "SYSTEM NAME",
  "subtitle": "One line describing what this system does",
  "components": [
    {{"icon": "brain", "name": "Component", "role": "what it does", "tags": ["tag1", "tag2"]}},
    {{"icon": "search", "name": "Component", "role": "what it does", "tags": ["tag1"]}},
    {{"icon": "agent", "name": "Component", "role": "what it does", "tags": ["tag1", "tag2"]}},
    {{"icon": "send", "name": "Component", "role": "what it does", "tags": ["tag1"]}}
  ],
  "_icon_note": "icon must be one of: brain search pencil check send chart database api agent flow memory user",
  "footer_insight": "One key architectural insight from the post"
}}

For build_card:
{{
  "type": "build_card",
  "day": "27",
  "project": "Project name — what you're building",
  "built": [
    {{"text": "Feature shipped", "sub": "optional detail"}},
    {{"text": "Feature shipped", "sub": ""}},
    {{"text": "Feature shipped", "sub": ""}}
  ],
  "next": [
    {{"text": "What comes next", "sub": "optional detail"}},
    {{"text": "What comes next", "sub": ""}},
    {{"text": "What comes next", "sub": ""}}
  ]
}}

For lesson_card:
{{
  "type": "lesson_card",
  "lesson_number": "12",
  "headline": "3-6 words. Bold punchline.",
  "body": "2-3 sentences expanding the lesson. Keep it direct.",
  "context": "Where this came from — project, situation, or stack"
}}

For comparison_card:
{{
  "type": "comparison_card",
  "left_name": "Option A",
  "right_name": "Option B",
  "rows": [
    {{"left": "left property", "right": "right property"}},
    {{"left": "left property", "right": "right property"}},
    {{"left": "left property", "right": "right property"}},
    {{"left": "left property", "right": "right property"}},
    {{"left": "left property", "right": "right property"}}
  ],
  "verdict": "The bottom line: one sentence summary of which to pick and when."
}}"""


_PLATFORM_DIMENSIONS: dict[str, tuple[int, int]] = {
    "linkedin":            (1200, 1200),   # square carousel slide
    "linkedin_landscape":  (1200, 627),    # single landscape post
    "linkedin_portrait":   (1080, 1350),   # portrait carousel
    "instagram":           (1080, 1080),   # square
    "instagram_portrait":  (1080, 1350),   # portrait
    "default":             (1200, 1200),
}


class InfographicAgent:

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

    def generate(self, post_text: str, platform: str = "default",
                 style: str = "linear_dark") -> str:
        """Legacy: extract structure from post text, then render."""
        data = self._extract_structure(post_text)
        return self.render_direct(data.get("type", "concept_card"), data,
                                  platform=platform, style=style)

    def render_direct(self, template_type: str, card_data: dict,
                      platform: str = "default", style: str = "linear_dark") -> str:
        """New flow: card data already structured, skip extraction."""
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

    def _generate_illustration(self, concept: str) -> str | None:
        """Generate illustration, return as base64 data URI or None on failure."""
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
        response = self._groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": _STRUCTURE_PROMPT.format(post_text=post_text),
            }],
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

    def _render(self, template_type: str, data: dict,
                platform: str = "default", style: str = "linear_dark") -> str:
        from agents.style_agent import StyleAgent
        w, h = _PLATFORM_DIMENSIONS.get(platform, _PLATFORM_DIMENSIONS["default"])
        base_css_url = (self._templates_dir / "_base.css").as_uri()
        sa = StyleAgent()

        extra: dict = {}
        if template_type == "architecture_card_v2":
            from agents.svg_layout import compute_layout
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

        template = self._env.get_template(f"{template_type}/template.html")
        return template.render(
            base_css_url=base_css_url,
            canvas_w=w, canvas_h=h,
            style_css=sa.css_overrides(style),
            body_class=sa.body_class(style),
            **extra,
            **data,
        )

    def _screenshot(self, html: str, label: str = "card", platform: str = "default") -> str:
        w, h = _PLATFORM_DIMENSIONS.get(platform, _PLATFORM_DIMENSIONS["default"])
        out_path = self._output_dir / f"{label}_{int(time.time())}.png"
        # Write to a real file so file:// relative imports in _base.css resolve correctly.
        # page.set_content() has no base_url — page.goto(file://) does.
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
