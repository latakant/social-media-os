import os
import time
from pathlib import Path

import requests
from groq import Groq


_PROMPT_TEMPLATE = """You are an art director. Read this LinkedIn post and generate a specific, clear image prompt for FLUX image generator.

POST:
{post_text}

Step 1 — Identify the CORE CONCEPT: What is the one central idea? (e.g. hierarchical orchestration, bottleneck problem, scaling pattern)
Step 2 — Design a visual that makes that concept immediately obvious to a viewer with no text.

Rules for the prompt:
- NO text, NO letters, NO labels, NO words anywhere in the image
- Be SPECIFIC about the visual structure (e.g. "three-tier pyramid of glowing nodes, top node connects to two mid nodes, each mid node connects to three bottom nodes")
- Specify exact colors, lighting, composition
- Style: clean isometric 3D illustration, dark navy background, electric blue and cyan glow
- The image must clearly show the STRUCTURE or CONCEPT, not just random tech nodes

Return ONLY the image generation prompt. No explanation. No preamble. Max 100 words."""

_HF_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"


class ImageAgent:

    def __init__(self, output_dir: str = "data/images") -> None:
        self._groq = Groq()
        self._hf_token = os.environ["HF_TOKEN"]
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, post_text: str) -> str:
        """Generate an image aligned to the post topic. Returns local file path."""
        prompt = self._build_prompt(post_text)
        print(f"Image prompt: {prompt[:80]}...")

        resp = requests.post(
            _HF_URL,
            headers={"Authorization": f"Bearer {self._hf_token}"},
            json={"inputs": prompt},
            timeout=120,
        )

        if resp.status_code == 503:
            # Model loading — wait and retry once
            print("Model loading, retrying in 20s...")
            time.sleep(20)
            resp = requests.post(
                _HF_URL,
                headers={"Authorization": f"Bearer {self._hf_token}"},
                json={"inputs": prompt},
                timeout=120,
            )

        if resp.status_code != 200:
            raise RuntimeError(f"HF image generation failed {resp.status_code}: {resp.text[:200]}")

        path = self._output_dir / f"post_{int(time.time())}.jpg"
        path.write_bytes(resp.content)
        print(f"Image saved: {path}")
        return str(path)

    def _build_prompt(self, post_text: str) -> str:
        response = self._groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(post_text=post_text[:600]),
            }],
        )
        return response.choices[0].message.content.strip()
