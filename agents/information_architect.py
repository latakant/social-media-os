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
    "architecture — system components with directed data/control flow (RAG, multi-agent, microservices, MCP)",
    "process_flow — decision/branching workflow (algorithm, decision tree, if/else logic)",
    "hierarchy    — nested/categorized concepts (layers, taxonomies, levels)",
)

_ICONS = "brain search pencil check send chart database api agent flow memory user"

_PROMPT = """You are an information architect for educational infographics targeting software engineers.

Use your real knowledge of the topic to produce accurate, specific content — not generic placeholders.
For well-known systems (MCP = Model Context Protocol, RAG, LangGraph, Kubernetes, etc.) use their
actual components, not invented ones.

Turn this content contract into a rich ContentGraph that a renderer can use to produce a professional infographic.

CONTENT CONTRACT:
{contract_json}

Detect the best visual pattern from these options:
{patterns}

Return ONLY valid JSON — no explanation, no markdown:
{{
  "hero": "MAIN VISUAL TITLE (2-4 words, ALL CAPS — must reflect the topic directly, e.g. MCP EXPLAINED not 'ARCHITECTURE OVERVIEW')",
  "subtitle": "One line — what this covers and why it matters",
  "pattern": "one of: lifecycle cheatsheet comparison architecture process_flow hierarchy",
  "phases": [
    {{ "name": "Phase Name", "node_ids": ["id1", "id2"] }}
  ],
  "nodes": [
    {{ "id": "unique_id", "label": "Short Label", "detail": "One specific sentence — what this component does", "icon": "icon_name", "phase": "phase_name or null" }}
  ],
  "edges": [
    {{ "from": "id1", "to": "id2" }}
  ],
  "example": {{
    "code_lang": "python",
    "code": "one_line_example()",
    "explanation": "what this demonstrates"
  }},
  "key_takeaways": ["One sentence insight", "One sentence insight", "One sentence insight"]
}}

Rules:
- nodes: MINIMUM 6, ideally 7-8 — every major component or step must be a node
- architecture: use 2-4 phases as columns (e.g. Client Layer / Protocol / Server Layer / Resources)
- lifecycle/process_flow: create 2-3 phases grouping the nodes
- cheatsheet/hierarchy: create 2-3 category phases
- hero MUST be derived from the actual topic name — never invent a generic title
- node detail must be specific and informative, not vague ("Tracks AI agent status" is too vague — write what it actually does)
- icon must be one of: {icons}
- edges define flow for lifecycle, process_flow, AND architecture patterns
- for architecture: every node must connect via at least one edge
- example.code: use a real, specific code example for the topic if one exists
- key_takeaways: exactly 3 standalone insight sentences"""


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
