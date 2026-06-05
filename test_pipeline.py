"""Quick pipeline test — runs topic through the full image generation stack.

Usage:
  python test_pipeline.py
  python test_pipeline.py "LangGraph vs LangChain"
  python test_pipeline.py "Spring Boot Deployment Lifecycle"
"""

import json
import sys
from dotenv import load_dotenv

from agents.planner import PlannerAgent
from agents.information_architect import InformationArchitectAgent
from agents.layout_agent import LayoutAgent
from agents.infographic import InfographicAgent

load_dotenv()

DIV = "=" * 52


def run(topic: str) -> None:
    print(f"\n{DIV}")
    print(f"Topic: {topic}")
    print(f"{DIV}\n")

    print("1. Planning...")
    contract = PlannerAgent().plan(topic)
    print(f"   content_type : {contract['content_type']}")
    print(f"   core_insight : {contract['core_insight'][:80]}")

    print("\n2. Information Architecture...")
    graph = InformationArchitectAgent().extract(contract)
    print(f"   pattern  : {graph['pattern']}")
    print(f"   hero     : {graph['hero']}")
    print(f"   nodes    : {len(graph.get('nodes', []))}")
    print(f"   phases   : {len(graph.get('phases', []))}")
    if graph.get('key_takeaways'):
        print(f"   takeaway : {graph['key_takeaways'][0][:80]}")

    print("\n   ContentGraph nodes:")
    for n in graph.get('nodes', []):
        phase = f"  [{n.get('phase','—')}]" if n.get('phase') else ""
        print(f"     {n['icon']:8} {n['label']:25} {n.get('detail','')[:45]}{phase}")

    print("\n3. Layout...")
    template_name, card_data = LayoutAgent().transform(graph)
    print(f"   template : {template_name}")
    print(f"   fields   : {[k for k in card_data.keys() if k != 'type']}")

    print("\n4. Rendering image...")
    image_path = InfographicAgent().render_direct(template_name, card_data, platform="linkedin")
    print(f"\n{DIV}")
    print(f"Image: {image_path}")
    print(f"{DIV}\n")

    # Dump ContentGraph for inspection
    graph_path = f"data/images/graph_{int(__import__('time').time())}.json"
    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump({"contract": contract, "graph": graph,
                   "template": template_name, "card_data": card_data}, f, indent=2)
    print(f"Graph : {graph_path}\n")


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "ReAct — the reasoning pattern behind most AI agents"
    run(topic)
