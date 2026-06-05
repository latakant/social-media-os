"""Social Media OS — Orchestrator.

One ContentContract in → N platform posts out.

Usage:
    await Orchestrator().run("AI Agents", platforms=["linkedin", "instagram"])
"""

import asyncio
import concurrent.futures
import os
import urllib.request

from agents.adapters.instagram_adapter import InstagramAdapter
from agents.adapters.linkedin_adapter import LinkedInAdapter
from agents.content_generator import ContentGenerator
from agents.infographic import InfographicAgent
from agents.knowledge_curator import KnowledgeCuratorAgent
from agents.planner import PlannerAgent
from agents.protocols import PlatformAgent
from agents.review import ReviewAgent
from bots.telegram_approval import ApprovalBot
from memory.store import update_platform_post_id
from publishers.base import PublishError, PublishResult, Publisher
from publishers.instagram import InstagramPublisher
from publishers.linkedin import LinkedInPublisher

_ADAPTERS: dict[str, type[PlatformAgent]] = {
    "linkedin": LinkedInAdapter,
    "instagram": InstagramAdapter,
}

_PUBLISHERS: dict[str, type[Publisher]] = {
    "linkedin": LinkedInPublisher,
    "instagram": InstagramPublisher,
}

DIV  = "=" * 52
DIV2 = "-" * 52


class Orchestrator:

    def __init__(self) -> None:
        self._curator   = KnowledgeCuratorAgent()
        self._planner   = PlannerAgent()
        self._content   = ContentGenerator()
        self._infograph = InfographicAgent()
        self._reviewer  = ReviewAgent()
        self._bot       = ApprovalBot()
        self._clear_telegram_session()

    async def run(
        self,
        topic: str,
        platforms: list[str],
        audience: str = "developers",
        objective: str = "thought_leadership",
    ) -> dict[str, PublishResult]:
        print(f"\n{DIV}")
        print("Social Media OS")
        print(f"{DIV}\n")

        # ── 0. Knowledge Curator ────────────────────────────────
        kg_node = self._curator.find_node(topic) or self._curator.pick_next()
        if kg_node:
            print(f"Knowledge node: [{kg_node['layer_name']}] {kg_node['topic']}")
            topic = self._curator.enrich_input(topic, kg_node)

        valid_platforms = [p for p in platforms if p in _ADAPTERS]
        print(f"Idea:      {topic.splitlines()[0]}")
        print(f"Platforms: {', '.join(valid_platforms)}\n")

        # ── 1. Plan → Content Contract ──────────────────────────
        print("Planning...")
        contract = self._planner.plan(topic)
        contract["_kg_node_id"]  = kg_node["id"] if kg_node else None
        contract["audience"]     = audience
        contract["objective"]    = objective
        contract["platforms"]    = valid_platforms
        print(f"  Topic:   {contract['topic']}")
        print(f"  Type:    {contract['content_type']}")
        print(f"  Insight: {contract['core_insight']}\n")

        # ── 2. Card structure + image ────────────────────────────
        print("Generating content structure...")
        template_name, card_data = self._content.generate(contract)
        print(f"  Template: {template_name}")

        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            image_result = await loop.run_in_executor(
                pool, self._infograph.render_direct, template_name, card_data
            )

        image_path: str | None = None
        if isinstance(image_result, Exception):
            print(f"  Image failed: {image_result}")
        else:
            image_path = image_result
            print(f"  Image: {image_path}")
        print()

        # ── 3. Platform content — parallel ──────────────────────
        print("Generating platform content...")
        drafts: dict[str, str] = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(valid_platforms)) as pool:
            futures = {p: pool.submit(_ADAPTERS[p]().adapt, contract) for p in valid_platforms}
            for platform, future in futures.items():
                try:
                    drafts[platform] = future.result()
                    print(f"  {platform}: {len(drafts[platform].split())} words")
                except Exception as exc:
                    print(f"  {platform}: failed — {exc}")
        print()

        # ── 4. Review ────────────────────────────────────────────
        print("Reviewing...")
        approved: dict[str, str] = {}
        for platform, text in drafts.items():
            review = self._reviewer.review(text, platform=platform)
            status = review.verdict
            print(f"  {platform}: {status}")
            for issue in review.issues:
                print(f"    ! {issue}")
            if status != "REJECT":
                approved[platform] = text
        print()

        if not approved:
            print("All drafts rejected. Adjust input and retry.")
            return {}

        # ── 5. Telegram approval + publish per platform ──────────
        published: dict[str, PublishResult] = {}

        for platform, text in approved.items():
            print(f"{DIV2}")
            print(f"DRAFT — {platform.upper()}")
            print(f"{DIV2}")
            print(text)
            print(f"{DIV2}\n")

            print(f"Sending {platform} to Telegram...")
            current_text = text
            attempt = 0

            while True:
                attempt += 1
                decision, post_id, suggestion = await self._bot.send_for_approval(
                    current_text, image_path, platform=platform
                )
                print(f"Decision ({platform}): {decision.upper()}")

                if decision == "approve":
                    break

                if decision == "reject":
                    print(f"  {platform}: rejected — skipping.")
                    current_text = None
                    break

                if decision == "redraft":
                    if attempt >= 4:
                        print("  4 redraft attempts reached — skipping.")
                        current_text = None
                        break

                    if suggestion:
                        contract["_suggestion"] = suggestion

                    print(f"  Redrafting {platform} (attempt {attempt + 1})...")
                    current_text = _ADAPTERS[platform]().adapt(contract)
                    review = self._reviewer.review(current_text, platform=platform)
                    print(f"  Review: {review.verdict}")
                    if review.verdict == "REJECT":
                        print("  Still rejected — skipping.")
                        current_text = None
                        break

                    print(f"\n{DIV2}")
                    print(f"REVISED — {platform.upper()}")
                    print(f"{DIV2}")
                    print(current_text)
                    print(f"{DIV2}\n")

            if not current_text:
                continue

            if platform not in _PUBLISHERS:
                print(f"  {platform}: no publisher configured — post manually.")
                continue

            print(f"Publishing to {platform}...")
            try:
                result = _PUBLISHERS[platform]().post(current_text, image_path=image_path)
                update_platform_post_id(post_id, result.platform_post_id)
                print(f"  Live: {result.platform_post_id}")
                published[platform] = result
            except PublishError as exc:
                print(f"  {platform} publish failed: {exc}")

        # ── 6. Mark knowledge graph node ────────────────────────
        if kg_node and published:
            first_id = next(iter(published.values())).platform_post_id
            self._curator.mark_posted(kg_node["id"], first_id)
            print(f"\nKnowledge graph: {kg_node['id']} → posted")

        print(f"\n{DIV}")
        print("Done.")
        print(f"{DIV}\n")

        return published

    # ── Internal ────────────────────────────────────────────────────────────

    @staticmethod
    def _clear_telegram_session() -> None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            return
        try:
            url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
            urllib.request.urlopen(url, timeout=5)
        except Exception:
            pass
