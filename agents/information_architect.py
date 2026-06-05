"""InformationArchitectAgent — transforms a content contract into a ContentGraph.

The ContentGraph is the most valuable asset in the pipeline. It encodes:
- visual pattern (lifecycle, cheatsheet, comparison, architecture, ...)
- nodes with icons, labels, details
- phase groupings
- edges (flow between nodes)
- code example
- key takeaways

Everything downstream (LayoutAgent, Renderer) is driven by this graph.
"""

import json
from groq import Groq


_PATTERNS = (
    "lifecycle    — sequential steps with phases (CI/CD, deployment, agent workflow, user journey)",
    "cheatsheet   — reference grid by category (API methods, commands, patterns, syntax)",
    "comparison   — two options side by side (A vs B, old way vs new way)",
    "architecture — system components and relationships (multi-agent, microservices, pipeline)",
    "process_flow — decision/branching workflow (algorithm, decision tree, if/else logic)",
    "hierarchy    — nested/categorized concepts (layers, taxonomies, levels)",
)

_ICONS = "brain search pencil check send chart database api agent flow memory user"

_PROMPT = """You are an information architect for educational infographics.

Turn this content contract into a rich ContentGraph that a renderer can use to produce a professional infographic.

CONTENT CONTRACT:
{contract_json}

Detect the best visual pattern from these options:
{patterns}

Return ONLY valid JSON — no explanation, no markdown:
{{
  "hero": "MAIN VISUAL TITLE (2-4 words, ALL CAPS, visual punch — e.g. REACT EXPLAINED, not 'What is React')",
  "subtitle": "One line — what this covers and why it matters",
  "pattern": "one of: lifecycle cheatsheet comparison architecture process_flow hierarchy",
  "phases": [
    {{ "name": "Phase Name", "node_ids": ["id1", "id2"] }}
  ],
  "nodes": [
    {{ "id": "unique_id", "label": "Short Label", "detail": "One line description", "icon": "icon_name", "phase": "phase_name or null" }}
  ],
  "edges": [
    {{ "from": "id1", "to": "id2" }}
  ],
  "example": {{
    "code_lang": "python",
    "code": "one_line_example()",
    "explanation": "what this demonstrates"
  }},
  "key_takeaways": ["One sentence insight", "One sentence insight"]
}}

Rules:
- nodes: 4-10 items (6-8 ideal for visual density)
- lifecycle/process_flow: create 2-3 phases grouping the nodes
- cheatsheet/hierarchy: create 2-3 category phases
- comparison/architecture: phases optional
- hero is the visual headline, not the topic verbatim
- icon must be one of: {icons}
- edges define flow for lifecycle and process_flow patterns
- example.code may be empty string if not applicable
- key_takeaways: 1-2 standalone insight sentences"""


class InformationArchitectAgent:

    def __init__(self) -> None:
        self._client = Groq()

    def extract(self, contract: dict) -> dict:
        """Extract a ContentGraph from a content contract."""
        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": _PROMPT.format(
                    contract_json=json.dumps(contract, indent=2),
                    patterns="\n".join(f"  - {p}" for p in _PATTERNS),
                    icons=_ICONS,
                ),
            }],
        )
        graph = json.loads(response.choices[0].message.content)
        # carry forward fields the rest of the pipeline needs
        graph["topic"]        = contract.get("topic", "")
        graph["content_type"] = contract.get("content_type", "concept")
        return graph
