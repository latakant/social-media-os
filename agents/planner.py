import json
from groq import Groq


_PROMPT = """You are a content strategist for a technical founder who builds AI agents and posts about it publicly.

USER IDEA:
{user_input}

Your job: extract a Master Content Contract from this idea.

Content types:
- "concept"      — explaining what something IS (MCP, RAG, ReAct, Agents, LangGraph, Memory)
- "architecture" — system design, pipeline flows, multi-agent patterns
- "build_update" — progress on something being built (no day numbers — topic focused)
- "lesson"       — insight, mistake, or hard lesson from building
- "comparison"   — A vs B (LangGraph vs LangChain, MCP vs APIs, RAG vs fine-tuning)

Return ONLY valid JSON:
{{
  "topic": "Short topic title — what this content is about (NOT 'Day X')",
  "content_type": "one of the 5 types above",
  "core_insight": "One sentence — the single most important thing to know about this topic",
  "key_points": ["point 1", "point 2", "point 3", "point 4"],
  "call_to_action": "One direct question to the reader about this specific topic",
  "supporting_details": {{
    // content_type specific data:
    // concept:      {{"concept_name": "REACT", "steps": ["Think", "Act", "Observe", "Repeat"]}}
    // architecture: {{"system_name": "Social Media Agent", "components": ["Analyst", "Writer", "Reviewer", "Publisher"]}}
    // build_update: {{"what_built": ["item1", "item2"], "what_next": ["item1", "item2"], "project": "project name"}}
    // lesson:       {{"lesson_number": "18", "headline": "3-6 word punchline", "what_happened": "brief story"}}
    // comparison:   {{"left": "LangChain", "right": "LangGraph", "dimensions": ["dim1", "dim2", "dim3"]}}
  }}
}}"""


class PlannerAgent:

    def __init__(self) -> None:
        self._client = Groq()

    def plan(self, user_input: str) -> dict:
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": _PROMPT.format(user_input=user_input),
            }],
        )
        return json.loads(response.choices[0].message.content)
