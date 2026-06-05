"""VisualBlock — the atomic content unit in the Content Layer.

One ContentGraph node → multiple VisualBlocks.
One VisualBlock → one carousel slide or one infographic panel.

The block type determines the visual layout; all downstream renderers
pattern-match on type without inspecting the content.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


BlockType = Literal[
    "what",        # definition — large title + explanation
    "why",         # motivation — checkmark bullet list
    "inputs",      # prerequisites — icon + label list
    "outputs",     # results — icon + label list
    "flow",        # sequence — numbered steps with arrows
    "example",     # code/real-world — terminal-style block
    "mistakes",    # anti-patterns — ✗ bullet list
    "comparison",  # two-column A vs B
    "takeaway",    # closing statement — single bold insight
]


@dataclass
class VisualBlock:
    """Atomic unit of content. One block = one carousel slide."""
    type: BlockType
    title: str              # slide headline, e.g. "What is HLD?"

    # Populated based on type — unused fields stay empty/default
    points:    list[str] = field(default_factory=list)  # why / inputs / outputs / mistakes
    flow:      list[str] = field(default_factory=list)  # flow: ordered step labels
    code:      str = ""                                  # example: code snippet
    code_lang: str = ""                                  # example: language hint
    caption:   str = ""                                  # example / comparison: explanatory line
    highlight: str = ""                                  # takeaway: the single bold sentence
    left:      list[str] = field(default_factory=list)  # comparison: left column
    right:     list[str] = field(default_factory=list)  # comparison: right column
    left_label:  str = ""                                # comparison: left header
    right_label: str = ""                                # comparison: right header
    icon:      str = "agent"                             # SVG icon name for visual accent

    # Structured per-item list — preferred over points when populated.
    # Each dict: {label: str, detail: str, icon: str}
    point_items: list[dict] = field(default_factory=list)

    order: int = 0          # position in the carousel (0-indexed)
    topic: str = ""         # parent topic — shown in footer


@dataclass
class Carousel:
    """Ordered sequence of VisualBlocks for one concept."""
    topic: str
    hero: str               # ALL-CAPS visual title from ContentGraph
    blocks: list[VisualBlock] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.blocks)
