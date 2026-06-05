from pathlib import Path

from groq import Groq

from schemas.reports import ObservationReport


_PROMPT = """You are a ghostwriter for a technical founder. Write one {platform} post.

BRAND VOICE (follow this exactly):
{brand_voice}

AUDIENCE INTELLIGENCE (use this to decide format, timing context, and what resonates — do NOT write about this):
- What works: {top_priority}
- Key findings: {findings}

YOUR JOB:
Pick one topic from the "Topics You Own" section of the brand voice above.
Write a post that shares a genuine insight, lesson, or observation from the creator's work.

Do NOT write about social media strategy, content audits, or engagement metrics.
Do NOT reference "our account" or "our content".
Write as an expert sharing what they actually know — architecture, systems, AI, building products.

Rules:
- Output only the post text — no title, no label, no explanation before or after
- No hashtags
- No emojis
- {platform} length: 150–250 words
- Concrete before abstract. Conclusion first, reasoning second."""


class ContentAgent:

    def __init__(self, brand_voice_path: str = "knowledge/brand_voice.md") -> None:
        self._client = Groq()
        self._brand_voice = Path(brand_voice_path).read_text(encoding="utf-8")

    def generate(self, report: ObservationReport, platform: str = "linkedin") -> str:
        findings_text = "\n".join(
            f"- [{f.signal_strength}] {f.observation}" for f in report.findings
        )
        recommendations_text = "\n".join(f"- {r}" for r in report.recommendations)

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT.format(
                        platform=platform,
                        brand_voice=self._brand_voice,
                        top_priority=report.top_priority,
                        findings=findings_text,
                        recommendations=recommendations_text,
                    ),
                }
            ],
        )

        return response.choices[0].message.content.strip()
