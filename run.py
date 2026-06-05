"""Social Intelligence Agent — Content Pyramid

Flow: User Idea → Master Contract → [Image || LinkedIn Post] → Review → Approve → Publish

Usage:
  python run.py
  python run.py "What is ReAct — reasoning pattern behind most AI agents"
  python run.py "LangGraph vs LangChain — when to use which"
  python run.py "Building Social Intelligence Agent — shipped Analyst, Content, Review agents"
  python run.py "Prompts are not the problem — state management is"
"""

import asyncio
import concurrent.futures
import os
import sys

from dotenv import load_dotenv

from agents.planner import PlannerAgent
from agents.knowledge_curator import KnowledgeCuratorAgent

def _clear_telegram_session() -> None:
    """Drop any stale Telegram getUpdates sessions before starting."""
    import urllib.request
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        urllib.request.urlopen(url, timeout=5)
    except Exception:
        pass
from agents.content_generator import ContentGenerator
from agents.adapters.linkedin_adapter import LinkedInAdapter
from agents.review import ReviewAgent
from agents.infographic import InfographicAgent
from bots.telegram_approval import ApprovalBot
from publishers.linkedin import LinkedInPublisher, PublishError
from memory.store import update_platform_post_id

load_dotenv()

DIV  = "=" * 52
DIV2 = "-" * 52


def linkedin_ready() -> bool:
    return bool(os.environ.get("LINKEDIN_ACCESS_TOKEN")) and \
           bool(os.environ.get("LINKEDIN_PERSON_URN"))


def _render_infographic(template_name: str, card_data: dict) -> str:
    return InfographicAgent().render_direct(template_name, card_data)


async def main(user_input: str) -> None:
    _clear_telegram_session()

    print(f"\n{DIV}")
    print("Social Intelligence Agent")
    print(f"{DIV}\n")

    # ── 0. Knowledge Curator → enrich input with graph context ──
    curator = KnowledgeCuratorAgent()
    kg_node: dict | None = curator.find_node(user_input) or curator.pick_next()

    if kg_node:
        print(f"Knowledge node: [{kg_node['layer_name']}] {kg_node['topic']}")
        user_input = curator.enrich_input(user_input, kg_node)
    else:
        print("No knowledge graph node found — proceeding without enrichment")

    print(f"Idea: {user_input.splitlines()[0]}\n")

    # ── 1. Planner → Master Content Contract ─────────────
    print("Planning...")
    contract = PlannerAgent().plan(user_input)
    if kg_node:
        contract["_kg_node_id"] = kg_node["id"]
    print(f"  Topic:   {contract['topic']}")
    print(f"  Type:    {contract['content_type']}")
    print(f"  Insight: {contract['core_insight']}\n")

    # ── 2. Content Generator → Card JSON (schema-constrained) ──
    print("Generating card structure...")
    template_name, card_data = ContentGenerator().generate(contract)
    print(f"  Template: {template_name}")
    print(f"  Fields:   {[k for k in card_data.keys() if k != 'type']}\n")

    # ── 3. Parallel: Image + LinkedIn Post from same contract ──
    print("Generating image and post in parallel...")
    loop = asyncio.get_event_loop()
    linkedin = LinkedInAdapter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        image_future = loop.run_in_executor(
            pool, _render_infographic, template_name, card_data
        )
        post_future = loop.run_in_executor(
            pool, linkedin.adapt, contract
        )
        image_result, post_result = await asyncio.gather(
            image_future, post_future, return_exceptions=True
        )

    image_path = None
    if isinstance(image_result, Exception):
        print(f"  Image failed: {image_result.__class__.__name__}: {str(image_result)[:80]}")
    else:
        image_path = image_result
        print(f"  Image: {image_path}")

    if isinstance(post_result, Exception):
        print(f"  Post failed: {post_result}")
        return

    post_text = post_result
    print(f"  Post:  {len(post_text.split())} words\n")

    # ── 4. Review ─────────────────────────────────────────
    print("Reviewing...")
    review = ReviewAgent().review(post_text, platform="linkedin")
    print(f"  Verdict: {review.verdict}")
    for issue in review.issues:
        print(f"  ! {issue}")
    print()

    if review.verdict == "REJECT":
        print("Rejected by Review Agent. Adjust input and retry.")
        return

    # ── 5. Show draft ─────────────────────────────────────
    print(f"{DIV2}")
    print("POST")
    print(f"{DIV2}")
    print(post_text)
    print(f"{DIV2}\n")

    # ── 6. Telegram — image + post together ───────────────
    print("Sending to Telegram...")
    bot = ApprovalBot()
    attempt = 0

    while True:
        attempt += 1
        decision, post_id, suggestion = await bot.send_for_approval(post_text, image_path)
        print(f"Decision: {decision.upper()}")

        if decision == "approve":
            break

        if decision == "reject":
            print("Rejected. Nothing published.")
            return

        if decision == "redraft":
            if attempt >= 4:
                print("4 redraft attempts reached. Stopping.")
                return

            print(f"Redrafting (attempt {attempt + 1})...")
            if suggestion:
                print(f"  Suggestion: {suggestion}")
                # Inject suggestion into contract as extra context
                contract["_suggestion"] = suggestion

            # Regenerate post only — reuse existing image
            post_text = LinkedInAdapter().adapt(contract)
            print(f"  New post: {len(post_text.split())} words")

            review = ReviewAgent().review(post_text, platform="linkedin")
            print(f"  Review: {review.verdict}")
            if review.verdict == "REJECT":
                print("  Still rejected. Try a different suggestion.")
                return

            print(f"\n{DIV2}")
            print("REVISED POST")
            print(f"{DIV2}")
            print(post_text)
            print(f"{DIV2}\n")
            continue

    print()

    # ── 7. Publish ────────────────────────────────────────
    if linkedin_ready():
        print("Publishing to LinkedIn...")
        try:
            result = LinkedInPublisher().post(post_text, image_path=image_path)
            update_platform_post_id(post_id, result.platform_post_id)
            print(f"Live: {result.platform_post_id}")
            if kg_node:
                curator.mark_posted(kg_node["id"], result.platform_post_id)
                print(f"Knowledge graph updated: {kg_node['id']} → posted")
        except PublishError as e:
            print(f"LinkedIn failed: {e}")
    else:
        print("LinkedIn not configured — post manually.")

    print(f"\n{DIV}")
    print("Done.")
    print(f"{DIV}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        suggestion = KnowledgeCuratorAgent().pick_next()
        if suggestion:
            print(f"Suggested next topic: {suggestion['topic']}")
            print(f"  Layer: {suggestion['layer_name']}  |  Importance: {suggestion['business']['importance']}/5")
            print(f"  Insight: {suggestion['core_insight']}")
            print()
        print("What do you want to post about today? (Enter to use suggestion)")
        user_input = input("> ").strip()
        if not user_input:
            if suggestion:
                user_input = suggestion["topic"]
                print(f"Using: {user_input}")
            else:
                print("No input and no suggestion available.")
                sys.exit(0)

    asyncio.run(main(user_input))
