from pathlib import Path
from groq import Groq


_PROMPT = """You are a ghostwriter for a technical AI founder writing on Instagram.

Write an Instagram caption from this content contract.

BRAND VOICE:
{brand_voice}

CONTENT CONTRACT:
Topic: {topic}
Type: {content_type}
Core Insight: {core_insight}
Key Points:
{key_points}
CTA: {call_to_action}

FORMAT:
[1-2 sentence hook — the single most important insight, stated directly]

[1-2 sentences expanding the most important key point. Specific and technical.]

[CTA: one direct question that invites a specific reply]

---
[3-5 hashtags, lowercase, specific to this topic]

Rules:
- Caption body: 40-80 words (before hashtags)
- No emojis
- No generic hashtags (#ai, #tech, #coding are too broad)
- Use specific hashtags: #agentarchitecture, #llmengineering, #reactagent, #multiagentsystems
- Tone: direct, technical, founder-led
- The visual carousel carries the detail — caption sets context and invites engagement
- No markdown formatting

Output only the caption followed by hashtags. Nothing else."""


class InstagramAdapter:

    def __init__(self, brand_voice_path: str = "knowledge/brand_voice.md") -> None:
        self._client = Groq()
        self._brand_voice = Path(brand_voice_path).read_text(encoding="utf-8")

    def adapt(self, contract: dict) -> str:
        key_points_text = "\n".join(f"- {p}" for p in contract.get("key_points", []))
        suggestion = contract.get("_suggestion")
        suggestion_block = (
            f"\nFEEDBACK FROM HUMAN REVIEWER (incorporate this):\n{suggestion}\n"
            if suggestion else ""
        )

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": _PROMPT.format(
                    brand_voice=self._brand_voice,
                    topic=contract["topic"],
                    content_type=contract["content_type"],
                    core_insight=contract["core_insight"],
                    key_points=key_points_text,
                    call_to_action=contract["call_to_action"],
                ) + suggestion_block,
            }],
        )
        return response.choices[0].message.content.strip()
