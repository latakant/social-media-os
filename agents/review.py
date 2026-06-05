import json
from pathlib import Path

from groq import Groq

from schemas.reports import ReviewResult


_LIMITS = {
    "linkedin": {"min_words": 80, "max_words": 300, "max_chars": 3000},
    "instagram": {"min_words": 10, "max_words": 80, "max_chars": 2200},
}

_PROMPT = """You are an editorial reviewer. Review this {platform} post draft against the brand voice below.

BRAND VOICE:
{brand_voice}

DRAFT:
{draft}

WORD COUNT: {word_count} words

Check every rule in the brand voice. Also check:
- Does the post start with a hook or state a conclusion? (not a question as opening)
- Is the tone direct and technical, not soft or corporate?
- Are there any emojis? (not allowed)
- Are there any hashtags? (not allowed)
- Does it end with a direct question or a specific link? (required)
- Is the word count between {min_words} and {max_words}?

Return JSON with this exact structure:
{{
  "verdict": "APPROVE|REVISE|REJECT",
  "passed": true|false,
  "issues": ["specific problem found", ...],
  "suggestions": ["specific fix for each issue", ...]
}}

Verdict rules:
- APPROVE: no issues, post is ready to send
- REVISE: 1–3 fixable issues, post has potential
- REJECT: wrong tone, wrong topic, or violates brand voice fundamentally

Be strict. Generic AI content should be REJECTED. Vague recommendations should be REVISE."""


class ReviewAgent:

    def __init__(self, brand_voice_path: str = "knowledge/brand_voice.md") -> None:
        self._client = Groq()
        self._brand_voice = Path(brand_voice_path).read_text(encoding="utf-8")

    def review(self, draft: str, platform: str = "linkedin") -> ReviewResult:
        limits = _LIMITS.get(platform, _LIMITS["linkedin"])
        word_count = len(draft.split())

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(
                        platform=platform,
                        brand_voice=self._brand_voice,
                        draft=draft,
                        word_count=word_count,
                        min_words=limits["min_words"],
                        max_words=limits["max_words"],
                    ),
                }
            ],
        )

        raw = json.loads(response.choices[0].message.content)

        return ReviewResult(
            verdict=raw["verdict"],
            passed=raw["passed"],
            issues=raw.get("issues", []),
            suggestions=raw.get("suggestions", []),
        )
