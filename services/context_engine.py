"""ContextEngine — assembles all context inputs before the first LLM call.

Single source of truth for what each agent sees. Moves scattered string
mutation out of Orchestrator and into one testable place.

Token budget controls how much context is included: analytics is dropped
first if the assembled string would exceed the budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


_BRAND_VOICE_PATH = Path("knowledge/brand_voice.md")
_DEFAULT_TOKEN_BUDGET = 2000  # ~4 chars per token


@dataclass
class ContentContext:
    topic: str
    audience: str
    objective: str
    style: str
    platforms: list[str]
    kg_node: dict | None = None
    analytics: dict | None = None
    brand_voice: str = ""

    def for_planner(self) -> str:
        """Return the enriched topic string PlannerAgent receives."""
        parts = [self.topic]

        if self.kg_node:
            n = self.kg_node
            lines = [
                "",
                "[Knowledge Graph Context]",
                f"Layer: {n['layer_name']} (Layer {n['layer']})",
                f"Core insight: {n['core_insight']}",
            ]
            prereqs = [
                self._node_topic(p)
                for p in n.get("prerequisites", [])
            ]
            if prereqs:
                lines.append(f"Builds on: {', '.join(prereqs)}")
            unlocks = [
                self._node_topic(u)
                for u in n.get("unlocks", [])[:3]
            ]
            if unlocks:
                lines.append(f"Leads to: {', '.join(unlocks)}")
            if n.get("templates"):
                lines.append(f"Preferred templates: {', '.join(n['templates'])}")
            parts.append("\n".join(lines))

        if self.analytics:
            a = self.analytics
            recs = "\n".join(f"- {r}" for r in a["recommendations"][:2])
            parts.append(
                f"\n[Analyst Context — based on recent {a['platform']} performance]"
                f"\nTop priority: {a['top_priority']}"
                f"\nRecent recommendations:\n{recs}"
            )

        return "\n".join(parts)

    def enrich_contract(self, contract: dict) -> dict:
        """Inject session context into the content contract.

        Called after PlannerAgent.plan() returns so the contract travels
        through the rest of the pipeline with full session state attached.
        """
        contract["audience"] = self.audience
        contract["objective"] = self.objective
        contract["platforms"] = self.platforms
        contract["style"] = self.style
        contract["_kg_node_id"] = self.kg_node["id"] if self.kg_node else None
        return contract

    def _node_topic(self, node_id: str) -> str:
        if self.kg_node and node_id == self.kg_node.get("id"):
            return self.kg_node.get("topic", node_id)
        return node_id.replace("_", " ")


class ContextEngine:

    @staticmethod
    def build(
        topic: str,
        *,
        kg_node: dict | None = None,
        analytics: dict | None = None,
        audience: str = "developers",
        objective: str = "thought_leadership",
        style: str = "linear_dark",
        platforms: list[str] | None = None,
        token_budget: int = _DEFAULT_TOKEN_BUDGET,
    ) -> ContentContext:
        brand_voice = (
            _BRAND_VOICE_PATH.read_text(encoding="utf-8")
            if _BRAND_VOICE_PATH.exists()
            else ""
        )

        # Drop analytics if base context already consumes most of the budget.
        # ~4 chars per token is a conservative estimate.
        chars_used = len(topic) + len(brand_voice)
        if kg_node:
            chars_used += len(str(kg_node))
        include_analytics = analytics is not None and (chars_used // 4) < token_budget - 300

        return ContentContext(
            topic=topic,
            audience=audience,
            objective=objective,
            style=style,
            platforms=platforms or ["linkedin"],
            kg_node=kg_node,
            analytics=analytics if include_analytics else None,
            brand_voice=brand_voice,
        )
