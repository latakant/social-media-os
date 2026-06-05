"""LayoutAgent — maps a ContentGraph to a (template_name, card_data) pair.

Template selection is rule-based (pattern → template).
Card data filling is an LLM call: graph → template schema.
Jinja2 is left as a pure renderer — no intelligence in templates.
"""

import json
from groq import Groq
from agents.template_registry import load_schema, schema_as_prompt


_PATTERN_TEMPLATE: dict[str, str] = {
    "lifecycle":    "lifecycle_card",
    "process_flow": "lifecycle_card",
    "cheatsheet":   "cheat_sheet_card",
    "hierarchy":    "cheat_sheet_card",
    "comparison":   "comparison_card",
    "architecture": "architecture_card",
    "concept":      "concept_card",
    "lesson":       "lesson_card",
    "build_update": "build_card",
}

_FALLBACK_CONTENT_TYPE_TEMPLATE: dict[str, str] = {
    "concept":      "concept_card",
    "architecture": "architecture_card",
    "build_update": "build_card",
    "lesson":       "lesson_card",
    "comparison":   "comparison_card",
}

_PROMPT = """You are a layout designer. Fill this infographic template using the ContentGraph.

CONTENT GRAPH:
{graph_json}

TARGET TEMPLATE: {template_name}

TEMPLATE SCHEMA:
{schema_desc}

Rules:
- Use graph.hero as the main title field (hero, concept_name, system_name, project, headline)
- Use graph.subtitle as the subtitle/tagline
- Map graph.nodes → template items (steps, components, items, rows)
- Map graph.phases → sections/categories where the template has them
- Use graph.key_takeaways[0] as footer_insight / key_insight / verdict / body
- Use graph.example.code as the code field if template has one
- Preserve icon names exactly from graph nodes (brain, search, pencil, etc.)
- Keep all text short — this goes on a visual card
- No markdown asterisks or formatting in string values

Return ONLY valid JSON matching the schema fields exactly."""


class LayoutAgent:

    def __init__(self) -> None:
        self._client = Groq()

    def transform(self, graph: dict) -> tuple[str, dict]:
        """Return (template_name, card_data) from a ContentGraph."""
        template_name = self._select_template(graph)
        card_data = self._fill_template(graph, template_name)
        card_data["type"] = template_name
        return template_name, self._clean(card_data)

    # ── Internal ────────────────────────────────────────────────────────────

    def _select_template(self, graph: dict) -> str:
        pattern = graph.get("pattern", "")
        if pattern in _PATTERN_TEMPLATE:
            return _PATTERN_TEMPLATE[pattern]
        content_type = graph.get("content_type", "")
        return _FALLBACK_CONTENT_TYPE_TEMPLATE.get(content_type, "concept_card")

    def _fill_template(self, graph: dict, template_name: str) -> dict:
        # Pass the full raw schema JSON so the LLM sees every nested field
        schema_desc = json.dumps(load_schema(template_name), indent=2)
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": _PROMPT.format(
                    graph_json=json.dumps(graph, indent=2),
                    template_name=template_name,
                    schema_desc=schema_desc,
                ),
            }],
        )
        return json.loads(response.choices[0].message.content)

    def _clean(self, obj):
        if isinstance(obj, str):
            return obj.replace("**", "").replace("__", "").replace("*", "").strip()
        if isinstance(obj, dict):
            return {k: self._clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._clean(i) for i in obj]
        return obj
