"""End-to-end carousel test with Telegram approval.

Flow:
  Topic → Plan → ContentGraph → VisualBlocks → Render slides → Telegram album → Human decision

Usage:
  python test_carousel_telegram.py
  python test_carousel_telegram.py "RAG Pipeline" --style modern_saas
  python test_carousel_telegram.py "MCP Architecture" --style technical_blueprint --platform instagram
"""

import asyncio, sys
from dotenv import load_dotenv

from agents.planner import PlannerAgent
from agents.information_architect import InformationArchitectAgent
from agents.visual_block_generator import VisualBlockGenerator
from renderers.block_renderer import BlockRenderer
from bots.telegram_approval import ApprovalBot

load_dotenv()

DIV = "=" * 52

def _clear_telegram_session() -> None:
    import os, urllib.request
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pass


async def main(topic: str, style: str, platform: str) -> None:
    _clear_telegram_session()

    print(f"\n{DIV}\nTopic: {topic}\nStyle: {style}  Platform: {platform}\n{DIV}\n")

    # ── 1. Plan ────────────────────────────────────────────────
    print("Planning...")
    contract = PlannerAgent().plan(topic)
    print(f"  type    : {contract['content_type']}")

    # ── 2. Content Graph ───────────────────────────────────────
    print("Information architecture...")
    graph = InformationArchitectAgent().extract(contract)
    print(f"  pattern : {graph['pattern']}")
    print(f"  hero    : {graph['hero']}")
    print(f"  nodes   : {len(graph.get('nodes') or [])}")

    # ── 3. Visual Blocks ───────────────────────────────────────
    print("Generating blocks...")
    carousel = VisualBlockGenerator().generate(graph)
    print(f"  slides  : {len(carousel)}")
    for b in carousel.blocks:
        print(f"  [{b.order+1:02d}] {b.type:12} '{b.title}'")

    # ── 4. Render (sync Playwright — must run in executor inside async) ──
    print("\nRendering slides...")
    import concurrent.futures
    loop = asyncio.get_event_loop()
    renderer = BlockRenderer()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        paths = await loop.run_in_executor(
            pool,
            lambda: renderer.render_carousel(carousel.blocks, platform=platform, style=style),
        )
    print(f"  {len(paths)} PNGs ready")

    # ── 5. Telegram ────────────────────────────────────────────
    print("\nSending to Telegram...")
    bot = ApprovalBot()
    decision, post_id, suggestion = await bot.send_carousel_for_approval(
        paths, topic=graph["hero"], platform=platform
    )

    print(f"\n{DIV}")
    print(f"Decision  : {decision.upper()}")
    print(f"Post ID   : {post_id}")
    if suggestion:
        print(f"Suggestion: {suggestion}")
    print(f"{DIV}\n")

    if decision == "approve":
        print("Carousel approved. Ready for publishing.")
    elif decision == "reject":
        print("Carousel rejected.")
    elif decision == "redraft":
        hint = f" — suggestion: {suggestion}" if suggestion else ""
        print(f"Redraft requested{hint}. Re-run with a refined topic or adjusted style.")


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
    asyncio.run(main(topic, style, platform))
