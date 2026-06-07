"""Social Media OS — CLI entry point.

Usage:
  python run.py
  python run.py "What is ReAct"
  python run.py "What is ReAct" --platforms linkedin instagram
"""

import asyncio
import sys

from dotenv import load_dotenv

from services.knowledge_service import KnowledgeService
from orchestrator import Orchestrator

load_dotenv()


def _parse_args() -> tuple[str, list[str], str]:
    args = sys.argv[1:]
    platforms: list[str] = ["linkedin"]
    style: str = "linear_dark"
    topic_parts: list[str] = []

    i = 0
    while i < len(args):
        if args[i] == "--platforms":
            platforms = []
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                platforms.append(args[i])
                i += 1
        elif args[i] == "--style" and i + 1 < len(args):
            style = args[i + 1]
            i += 2
        else:
            topic_parts.append(args[i])
            i += 1

    return " ".join(topic_parts), platforms, style


if __name__ == "__main__":
    topic, platforms, style = _parse_args()

    if not topic:
        suggestion = KnowledgeService().pick_next()
        if suggestion:
            print(f"Suggested next topic: {suggestion['topic']}")
            print(f"  Layer: {suggestion['layer_name']}  |  Importance: {suggestion['business']['importance']}/5")
            print(f"  Insight: {suggestion['core_insight']}")
            print()
        print("What do you want to post about today? (Enter to use suggestion)")
        topic = input("> ").strip()
        if not topic:
            if suggestion:
                topic = suggestion["topic"]
                print(f"Using: {topic}")
            else:
                print("No input.")
                sys.exit(0)

    asyncio.run(Orchestrator().run(topic, platforms=platforms, style=style))
