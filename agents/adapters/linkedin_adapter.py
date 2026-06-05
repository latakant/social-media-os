from pathlib import Path
from groq import Groq


_PROMPT = """You are a ghostwriter for a technical AI founder writing on LinkedIn.

Write one LinkedIn post from this content contract.

BRAND VOICE:
{brand_voice}

CONTENT CONTRACT:
Topic: {topic}
Type: {content_type}
Core Insight: {core_insight}
Key Points:
{key_points}
CTA: {call_to_action}

FORMAT (follow this structure exactly):
[Hook — one bold statement that challenges a common belief or states the core insight directly]

[blank line]

[2-3 short paragraphs expanding the key points. Each paragraph 1-3 sentences. Technical and specific.]

[blank line]

[Closing: the CTA question, direct and specific]

Rules:
- Hook must NOT start with "Day", "Today", "I've been", "On day"
- Hook states a sharp conclusion or contrast — makes reader stop scrolling
- Name specific things: agent names, tools, patterns — not vague generalities
- No hashtags. No emojis. No markdown formatting.
- 150-220 words total

Output only the post text. Nothing else."""


class LinkedInAdapter:

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
