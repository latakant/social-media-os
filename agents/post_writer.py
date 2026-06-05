from pathlib import Path
from groq import Groq


_PROMPT = """You are a ghostwriter for a technical founder who builds AI agents in public.

Write one LinkedIn post based on this card data. Match the voice of the EXAMPLE exactly.

BRAND VOICE:
{brand_voice}

EXAMPLE OF THE EXACT VOICE TO MATCH:
---
Most social media agents look like this: Prompt → LLM → Post → Done.

That is not intelligence. That is automation.

The system I built on Day 27 looks like this:
Observe → Analyze → Generate → Review → Approve → Publish → Measure → Learn

Each step is a separate agent with a single responsibility. The Analyst Agent reads Instagram metrics and produces a structured ObservationReport. The Content Agent drafts a post filtered through brand_voice.md. The Review Agent returns APPROVE, REVISE, or REJECT. The Telegram Bot puts a human in the loop before anything goes live.

The part that makes it a system rather than a tool: every post feeds the memory layer. Engagement data collected 48 hours later informs the next cycle.

Next: Engagement Collector, Memory Agent, MCP Server.

What is the hardest architectural decision you have made when building a multi-agent system?
---

CARD DATA (this is what the image shows):
Type: {content_type}
{card_json}

Rules:
- Match the EXAMPLE voice exactly — direct, technical, specific, no fluff
- Start with a sharp contrast or observation — never "On Day N" or "Today I"
- Name specific components and explain what they do architecturally
- Use short paragraphs, 1-3 sentences each
- End with ONE direct technical question
- No hashtags. No emojis. No markdown. No motivational language.
- Length: 150-220 words

Output only the post text. Nothing else."""


class PostWriter:

    def __init__(self, brand_voice_path: str = "knowledge/brand_voice.md") -> None:
        self._client = Groq()
        self._brand_voice = Path(brand_voice_path).read_text(encoding="utf-8")

    def write(self, content_type: str, card_data: dict) -> str:
        import json
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": _PROMPT.format(
                    brand_voice=self._brand_voice,
                    content_type=content_type,
                    card_json=json.dumps(card_data, indent=2),
                ),
            }],
        )
        return response.choices[0].message.content.strip()
