from pathlib import Path
from groq import Groq


_PROMPT = """You are a ghostwriter for a technical AI founder writing on LinkedIn.

Write one LinkedIn post from this content contract.

BRAND VOICE:
{brand_voice}

CONTENT CONTRACT:
Topic: {topic}
Type: {content_type}
Angle: {angle}
Core Insight: {core_insight}
Key Points:
{key_points}
CTA: {call_to_action}
{hook_block}
FORMAT (follow this structure exactly):
[Hook — first line of the post]

[blank line]

[2-3 short paragraphs expanding the key points. Each paragraph 1-3 sentences. Technical and specific.]

[blank line]

[Closing: the CTA question, direct and specific]

Rules:
- If a hook is provided above, use it exactly as the first line — do not paraphrase
- If no hook is provided, write one: a sharp conclusion or contrast that makes readers stop scrolling
- Hook must NOT start with "Day", "Today", "I've been", "On day"
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
        hook = contract.get("hook", "")
        hook_block = f"Opening Hook (use this exact line first):\n{hook}\n" if hook else ""
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
                    angle=contract.get("angle", "teach_pattern"),
                    core_insight=contract["core_insight"],
                    key_points=key_points_text,
                    call_to_action=contract["call_to_action"],
                    hook_block=hook_block,
                ) + suggestion_block,
            }],
        )
        return response.choices[0].message.content.strip()
