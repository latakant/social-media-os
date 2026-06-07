"""KnowledgeService — retrieves and traverses the knowledge graph.

Pure service: no LLM calls, no reasoning. Answers queries about the
curriculum graph (what to post next, prerequisites, related nodes).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


KG_PATH = Path("knowledge/knowledge_graph.json")


class KnowledgeService:

    def __init__(self) -> None:
        with open(KG_PATH) as f:
            self._graph = json.load(f)
        self._nodes: dict[str, dict] = {n["id"]: n for n in self._graph["nodes"]}

    # ── Public API ─────────────────────────────────────────────────────────

    def pick_next(self) -> dict | None:
        """Return the highest-priority unposted node whose prerequisites are met."""
        candidates = [
            n for n in self._graph["nodes"]
            if not n["posting"]["posted"] and self._prereqs_met(n)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda n: (n["business"]["importance"], -n["layer"]))

    def find_node(self, topic_hint: str) -> dict | None:
        """Match a user topic hint to a knowledge graph node (id or substring)."""
        hint = topic_hint.lower()
        if hint in self._nodes:
            return self._nodes[hint]
        for node in self._graph["nodes"]:
            if hint in node["topic"].lower() or hint in node["id"].replace("_", " "):
                return node
        return None

    def enrich_input(self, user_input: str, node: dict) -> str:
        """Append knowledge graph context to user input before planning."""
        lines = [user_input, "", "[Knowledge Graph Context]",
                 f"Layer: {node['layer_name']} (Layer {node['layer']})",
                 f"Core insight: {node['core_insight']}"]

        prereq_topics = [
            self._nodes[p]["topic"]
            for p in node.get("prerequisites", [])
            if p in self._nodes
        ]
        if prereq_topics:
            lines.append(f"Builds on: {', '.join(prereq_topics)}")

        unlock_topics = [
            self._nodes[u]["topic"]
            for u in node.get("unlocks", [])
            if u in self._nodes
        ]
        if unlock_topics:
            lines.append(f"Leads to: {', '.join(unlock_topics[:3])}")

        if node.get("templates"):
            lines.append(f"Preferred templates: {', '.join(node['templates'])}")

        return "\n".join(lines)

    def mark_posted(self, node_id: str, post_id: str) -> None:
        """Persist the posted state back to knowledge_graph.json."""
        node = self._nodes.get(node_id)
        if not node:
            return
        node["posting"]["posted"] = True
        node["posting"]["post_ids"].append(post_id)
        node["posting"]["posted_at"] = datetime.now(timezone.utc).isoformat()
        with open(KG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._graph, f, indent=2, ensure_ascii=False)

    # ── Internal ────────────────────────────────────────────────────────────

    def _prereqs_met(self, node: dict) -> bool:
        return all(
            self._nodes[p]["posting"]["posted"]
            for p in node.get("prerequisites", [])
            if p in self._nodes
        )
