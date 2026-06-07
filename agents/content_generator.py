import json
from groq import Groq
from services.template_registry import schema_as_prompt


# Maps content_type → template name
TEMPLATE_MAP = {
    "concept":      "concept_card",
    "architecture": "architecture_card",
    "build_update": "build_card",
    "lesson":       "lesson_card",
    "comparison":   "comparison_card",
}

_PROMPT = """You are a structured content generator. Fill in this infographic template from the content contract.

MASTER CONTENT CONTRACT:
{contract_json}

TEMPLATE TO FILL:
{schema}

Rules:
- Use the topic, core_insight, key_points, and supporting_details from the contract
- Do NOT invent information not present in the contract
- No day numbers as main focus — use the topic as the hero
- No markdown asterisks or formatting in string values
- Keep all text short and direct — this goes on a visual card
- Arrays must match the exact item structure shown in the schema

Return ONLY valid JSON matching the schema fields exactly."""


class ContentGenerator:

    def __init__(self) -> None:
        self._client = Groq()

    def generate(self, contract: dict) -> tuple[str, dict]:
        """Returns (template_name, card_data)."""
        content_type = contract["content_type"]
        template_name = TEMPLATE_MAP.get(content_type, "concept_card")
        schema_desc = schema_as_prompt(template_name)

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": _PROMPT.format(
                    contract_json=json.dumps(contract, indent=2),
                    schema=schema_desc,
                ),
            }],
        )
        data = json.loads(response.choices[0].message.content)
        data["type"] = template_name
        return template_name, self._clean(data)

    def _clean(self, obj):
        if isinstance(obj, str):
            return obj.replace("**", "").replace("__", "").replace("*", "").strip()
        if isinstance(obj, dict):
            return {k: self._clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._clean(i) for i in obj]
        return obj
