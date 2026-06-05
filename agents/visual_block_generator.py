"""VisualBlockGenerator — transforms a ContentGraph into a Carousel of VisualBlocks.

This is the Content Graph Service milestone: one topic → VisualBlock[] → any output format.

Rule-based mapping, no LLM call:
  - ContentGraph.pattern determines which block types to emit
  - ContentGraph fields map directly to block fields
  - Order follows the anatomy: what → why → flow/inputs → outputs → example → mistakes → takeaway
"""

from __future__ import annotations
from schemas.visual_block import BlockType, Carousel, VisualBlock


# Block sequence per pattern — defines which slides are generated and in what order
_PATTERN_SEQUENCE: dict[str, list[BlockType]] = {
    "lifecycle":    ["what", "why", "flow", "example", "takeaway"],
    "process_flow": ["what", "why", "flow", "example", "mistakes", "takeaway"],
    "architecture": ["what", "why", "flow", "example", "takeaway"],
    "cheatsheet":   ["what", "why", "outputs", "example", "takeaway"],
    "hierarchy":    ["what", "why", "inputs", "outputs", "takeaway"],
    "comparison":   ["what", "why", "comparison", "example", "takeaway"],
    "concept":      ["what", "why", "flow", "example", "mistakes", "takeaway"],
    "lesson":       ["what", "why", "example", "mistakes", "takeaway"],
    "build_update": ["what", "outputs", "flow", "takeaway"],
}

_ICON_MAP: dict[BlockType, str] = {
    "what":       "brain",
    "why":        "check",
    "inputs":     "database",
    "outputs":    "send",
    "flow":       "flow",
    "example":    "pencil",
    "mistakes":   "agent",
    "comparison": "chart",
    "takeaway":   "memory",
}


class VisualBlockGenerator:

    def generate(self, graph: dict) -> Carousel:
        """Convert a ContentGraph dict into a Carousel of VisualBlocks."""
        topic   = graph.get("topic", "")
        hero    = graph.get("hero", topic.upper())
        pattern = graph.get("pattern", "concept")
        sequence: list[BlockType] = _PATTERN_SEQUENCE.get(pattern, _PATTERN_SEQUENCE["concept"])

        raw: list[VisualBlock] = []
        for order, block_type in enumerate(sequence):
            block = self._build_block(block_type, graph, topic, order)
            if block:
                raw.append(block)

        # Re-number consecutively after skipped blocks
        for i, block in enumerate(raw):
            block.order = i

        return Carousel(topic=topic, hero=hero, blocks=raw)

    # ── Block builders ────────────────────────────────────────────────────

    def _build_block(
        self, block_type: BlockType, graph: dict, topic: str, order: int
    ) -> VisualBlock | None:
        icon = _ICON_MAP.get(block_type, "agent")
        base = dict(type=block_type, topic=topic, order=order, icon=icon)

        nodes    = graph.get("nodes") or []
        phases   = graph.get("phases") or []
        example  = graph.get("example") or {}
        hero     = graph.get("hero", "")
        subtitle = graph.get("subtitle", "")
        takeaways = graph.get("key_takeaways") or []

        if block_type == "what":
            return VisualBlock(
                title=f"What is {hero.title()}?",
                points=[subtitle] + [n["label"] for n in nodes[:4]],
                **base,
            )

        if block_type == "why":
            return VisualBlock(
                title=f"Why {hero.title()} matters",
                points=takeaways[:4] or [n["detail"] for n in nodes[:4]],
                **base,
            )

        if block_type == "inputs":
            return VisualBlock(
                title="Inputs",
                points=[n["label"] for n in nodes if n.get("phase") in
                        self._phase_names(phases, 0)],
                **base,
            ) if nodes else None

        if block_type == "outputs":
            return VisualBlock(
                title="Outputs",
                points=[n["label"] for n in nodes if n.get("phase") in
                        self._phase_names(phases, -1)],
                **base,
            ) if nodes else None

        if block_type == "flow":
            steps = [n["label"] for n in nodes]
            if not steps:
                return None
            return VisualBlock(title="How it works", flow=steps, **base)

        if block_type == "example":
            code = example.get("code", "")
            if not code:
                return None
            return VisualBlock(
                title="Example",
                code=code,
                code_lang=example.get("code_lang", ""),
                caption=example.get("explanation", ""),
                **base,
            )

        if block_type == "mistakes":
            return VisualBlock(
                title="Common Mistakes",
                points=[f"Skipping {n['label']}" for n in nodes[:4]],
                **base,
            ) if nodes else None

        if block_type == "comparison":
            mid = len(nodes) // 2
            left_nodes  = nodes[:mid]
            right_nodes = nodes[mid:]
            phase_names = [p["name"] for p in phases]
            left_label  = phase_names[0] if len(phase_names) > 0 else "Option A"
            right_label = phase_names[1] if len(phase_names) > 1 else "Option B"
            return VisualBlock(
                title=f"{left_label} vs {right_label}",
                left=[n["label"] for n in left_nodes],
                right=[n["label"] for n in right_nodes],
                left_label=left_label,
                right_label=right_label,
                caption=takeaways[0] if takeaways else "",
                **base,
            )

        if block_type == "takeaway":
            insight = takeaways[0] if takeaways else subtitle
            return VisualBlock(
                title="Key Takeaway",
                highlight=insight,
                **base,
            )

        return None

    def _phase_names(self, phases: list[dict], idx: int) -> list[str]:
        """Return the phase name at position idx (first or last)."""
        if not phases:
            return []
        try:
            return [phases[idx]["name"]]
        except (IndexError, KeyError):
            return []
