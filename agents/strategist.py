"""StrategistAgent — decides HOW to communicate a topic before planning content.

Replaces PlannerAgent. Takes ContentContext (structured) instead of a raw
string, so it can reason against brand voice, curriculum position, and
analytics in a single LLM call.

Adds three fields to the content contract:
  angle    — the specific lens to take on this topic
  hook     — the exact opening line, pre-decided before post-writing
  framing  — how to position the content for maximum resonance
"""

import json
from groq import Groq

from services.context_engine import ContentContext


_ANGLES = (
    "teach_pattern        — explain the system or concept with precision",
    "challenge_assumption — name a wrong belief developers hold, then correct it",
    "reveal_failure       — show a common mistake, explain why it happens, what to do",
    "show_architecture    — component breakdown, data flow, diagram-first thinking",
    "share_decision       — a real product/arch choice and the reasoning behind it",
    "compare_approaches   — two ways to solve the same problem, with explicit tradeoffs",
)

_CONTENT_TYPES = (
    "concept      — what something IS (MCP, RAG, ReAct, Agents, LangGraph, Memory)",
    "architecture — system design, pipeline flows, multi-agent patterns",
    "build_update — progress on something being built (topic-focused, no day numbers)",
    "lesson       — insight, mistake, or hard lesson from building",
    "comparison   — A vs B (LangGraph vs LangChain, RAG vs fine-tuning)",
)

_SYSTEM = """You are a content strategist for a technical founder who builds AI agents in public.

Decide HOW to communicate the given topic — not just what to say, but the specific angle
that creates the most impact given brand positioning and current performance data.

Always return valid JSON. No markdown. No explanation outside JSON."""

_PROMPT = """BRAND VOICE:
{brand_voice}

TOPIC: {topic}
AUDIENCE: {audience}
OBJECTIVE: {objective}
{kg_block}{analytics_block}
Choose the best angle:
{angles}

Content type options:
{content_types}

Return JSON with this exact schema:
{{
  "topic": "Short topic title (NOT 'Day X')",
  "content_type": "one of the 5 content types",
  "angle": "one of the 6 angles (key only, e.g. teach_pattern)",
  "hook": "Opening line — one sharp sentence that makes a developer stop scrolling. States a conclusion, challenges a belief, or names a failure. Must NOT start with 'Day', 'Today', 'I', 'Have you'.",
  "framing": "One sentence on how to position this content for maximum resonance given the angle",
  "core_insight": "One sentence — the single most important thing to know about this topic",
  "key_points": ["point 1", "point 2", "point 3", "point 4"],
  "call_to_action": "One direct question to the reader about this specific topic",
  "supporting_details": {{
    "concept:      {{}}: concept_name, steps[]",
    "architecture: {{}}: system_name, components[]",
    "build_update: {{}}: what_built[], what_next[], project",
    "lesson:       {{}}: lesson_number, headline, what_happened",
    "comparison:   {{}}: left, right, dimensions[]"
  }}
}}

Rules:
- hook is the most important field — invest reasoning here
- hook must be specific to the topic, not a generic opener
- angle and hook must be consistent with each other
- key_points: 3-5 items, each one specific and actionable
- supporting_details: match the structure for the chosen content_type"""


def _kg_block(ctx: ContentContext) -> str:
    if not ctx.kg_node:
        return ""
    n = ctx.kg_node
    lines = [
        "",
        "CURRICULUM POSITION (knowledge graph):",
        f"Layer: {n['layer_name']} (Layer {n['layer']})",
        f"Core insight: {n['core_insight']}",
    ]
    if n.get("templates"):
        lines.append(f"Visual hint: {', '.join(n['templates'])}")
    return "\n".join(lines) + "\n"


def _analytics_block(ctx: ContentContext) -> str:
    if not ctx.analytics:
        return ""
    a = ctx.analytics
    recs = "\n".join(f"  - {r}" for r in a["recommendations"][:3])
    return (
        f"\nANALYTICS CONTEXT (recent {a['platform']} performance):\n"
        f"Top priority: {a['top_priority']}\n"
        f"Recommendations:\n{recs}\n"
    )


class StrategistAgent:

    def __init__(self) -> None:
        self._client = Groq()

    def plan(self, ctx: ContentContext) -> dict:
        """Reason about angle + hook, then produce the full content contract."""
        prompt = _PROMPT.format(
            brand_voice=ctx.brand_voice or "(no brand voice on file)",
            topic=ctx.topic.splitlines()[0],
            audience=ctx.audience,
            objective=ctx.objective,
            kg_block=_kg_block(ctx),
            analytics_block=_analytics_block(ctx),
            angles="\n".join(f"  {a}" for a in _ANGLES),
            content_types="\n".join(f"  {t}" for t in _CONTENT_TYPES),
        )

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return json.loads(response.choices[0].message.content)
