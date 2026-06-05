"""Test the VisualBlock carousel pipeline end-to-end.

Usage:
  python test_carousel.py
  python test_carousel.py "RAG Pipeline" --style modern_saas
  python test_carousel.py "HLD vs LLD" --platform instagram
"""

import sys, json
from dotenv import load_dotenv
from agents.planner import PlannerAgent
from agents.information_architect import InformationArchitectAgent
from agents.visual_block_generator import VisualBlockGenerator
from agents.block_renderer import BlockRenderer

load_dotenv()

DIV = "=" * 52


def run(topic: str, style: str = "linear_dark", platform: str = "linkedin") -> None:
    print(f"\n{DIV}\nTopic: {topic}\nStyle: {style}  Platform: {platform}\n{DIV}\n")

    print("1. Planning...")
    contract = PlannerAgent().plan(topic)
    print(f"   type    : {contract['content_type']}")

    print("2. Information Architecture...")
    graph = InformationArchitectAgent().extract(contract)
    print(f"   pattern : {graph['pattern']}")
    print(f"   hero    : {graph['hero']}")
    print(f"   nodes   : {len(graph.get('nodes') or [])}")

    print("3. Generating Visual Blocks...")
    carousel = VisualBlockGenerator().generate(graph)
    print(f"   slides  : {len(carousel)}")
    for b in carousel.blocks:
        print(f"   [{b.order+1:02d}] {b.type:12} '{b.title}'")

    print("\n4. Rendering slides...")
    renderer = BlockRenderer()
    paths = renderer.render_carousel(carousel.blocks, platform=platform, style=style)

    print(f"\n{DIV}")
    print(f"Carousel: {len(paths)} slides")
    for p in paths:
        print(f"  {p}")
    print(f"{DIV}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    style, platform, topic_parts = "linear_dark", "linkedin", []
    i = 0
    while i < len(args):
        if args[i] == "--style" and i + 1 < len(args):
            style = args[i + 1]; i += 2
        elif args[i] == "--platform" and i + 1 < len(args):
            platform = args[i + 1]; i += 2
        else:
            topic_parts.append(args[i]); i += 1
    topic = " ".join(topic_parts) or "What is a RAG Pipeline"
    run(topic, style, platform)
