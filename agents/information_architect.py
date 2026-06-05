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

# Topic keywords that force cheatsheet pattern regardless of LLM detection
_CHEATSHEET_SIGNALS = [
    "cheat sheet", "cheatsheet", "quick reference", "reference guide",
    "commands", "methods", "syntax", "api reference", "all methods",
    "complete guide", "roadmap", "learning path",
]

_PROMPT = """You are an information architect for educational infographics targeting software engineers.

Use your real knowledge of the topic to produce accurate, specific content — not generic placeholders.
For well-known systems (MCP = Model Context Protocol, RAG, LangGraph, Kubernetes, etc.) use their
actual components, not invented ones.

Turn this content contract into a rich ContentGraph that a renderer can use to produce a professional infographic.

CONTENT CONTRACT:
{contract_json}

Detect the best visual pattern from these options:
{patterns}

Return ONLY valid JSON — no explanation, no markdown.

For NON-CHEATSHEET patterns (lifecycle, architecture, comparison, process_flow, hierarchy):
{{
  "hero": "MAIN VISUAL TITLE (2-4 words, ALL CAPS — must reflect the topic directly)",
  "subtitle": "One line — what this covers and why it matters",
  "pattern": "one of: lifecycle cheatsheet comparison architecture process_flow hierarchy",
  "phases": [ {{ "name": "Phase Name", "node_ids": ["id1", "id2"] }} ],
  "nodes": [ {{ "id": "unique_id", "label": "Short Label", "detail": "One specific sentence", "icon": "icon_name", "phase": "phase_name or null" }} ],
  "edges": [ {{ "from": "id1", "to": "id2" }} ],
  "sections": [],
  "example": {{ "code_lang": "python", "code": "one_line_example()", "explanation": "what this demonstrates" }},
  "key_takeaways": ["insight 1", "insight 2", "insight 3"],
  "footer_note": ""
}}

For CHEATSHEET and HIERARCHY patterns (API references, syntax guides, command references, learning roadmaps):
{{
  "hero": "TOPIC NAME ALL CAPS (e.g. JAVA STREAMS, GIT COMMANDS, PYTHON TIPS)",
  "subtitle": "One line — what this covers and target audience",
  "pattern": "cheatsheet",
  "phases": [],
  "nodes": [],
  "edges": [],
  "sections": [
    {{
      "name": "Section Title",
      "items": [
        {{ "name": "method() or term", "desc": "One short line — what it does" }},
        {{ "name": "method() or term", "desc": "One short line — what it does" }}
      ]
    }}
  ],
  "example": {{ "code_lang": "", "code": "", "explanation": "" }},
  "key_takeaways": ["insight 1", "insight 2", "insight 3"],
  "footer_note": "Short bottom note (e.g. Java 8+ — prefer streams over loops for clean functional code)"
}}

Rules for ALL patterns:
- hero MUST be derived from the actual topic name — never invent a generic title
- icon must be one of: {icons}
- key_takeaways: exactly 3 standalone insight sentences

Rules for NON-CHEATSHEET:
- nodes: MINIMUM 6, ideally 7-8
- architecture: 2-4 phases as columns
- lifecycle/process_flow: 2-3 phases
- node detail must be specific, not vague
- edges define flow — every node must connect via at least one edge

Rules for CHEATSHEET:
- sections: 6-9 sections (fills a 3-column grid well)
- items per section: 3-5 (readable density)
- item name: the exact method/command/term (use () for functions)
- item desc: one short specific sentence — what it does, not what it is called
- footer_note: version or usage tip"""


class InformationArchitectAgent:

    def __init__(self) -> None:
        self._client = Groq()

    def extract(self, contract: dict) -> dict:
        """Extract a ContentGraph from a content contract."""
        topic_lower = contract.get("topic", "").lower()
        forced_pattern = None
        if any(sig in topic_lower for sig in _CHEATSHEET_SIGNALS):
            forced_pattern = "cheatsheet"

        prompt = _PROMPT.format(
            contract_json=json.dumps(contract, indent=2),
            patterns="\n".join(f"  - {p}" for p in _PATTERNS),
            icons=_ICONS,
        )
        if forced_pattern:
            prompt += f"\n\nIMPORTANT: The topic explicitly requests a cheat sheet. You MUST use pattern: \"{forced_pattern}\" and populate the sections array, NOT nodes."

        response = self._client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        graph = json.loads(response.choices[0].message.content)
        # carry forward fields the rest of the pipeline needs
        graph["topic"]        = contract.get("topic", "")
        graph["content_type"] = contract.get("content_type", "concept")
        # Apply forced pattern override after LLM call
        if forced_pattern:
            graph["pattern"] = forced_pattern
        return graph
