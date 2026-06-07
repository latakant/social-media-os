"""Full pipeline: Instagram data -> Observe -> Draft -> Review -> Telegram -> LinkedIn

Run: python run_sprint1.py
Done condition: post live on LinkedIn, PostRecord has platform_post_id.
"""

import asyncio
import concurrent.futures
import json
import os
from datetime import datetime

from dotenv import load_dotenv

from schemas.instagram import InstagramSnapshot
from normalizers.instagram import InstagramNormalizer
from services.analytics_service import AnalyticsService
from agents.content import ContentAgent
from agents.infographic import InfographicAgent
from agents.review import ReviewAgent
from bots.telegram_approval import ApprovalBot
from publishers.linkedin import LinkedInPublisher, PublishError
from memory.store import update_platform_post_id

load_dotenv()


def load_snapshot(path: str) -> InstagramSnapshot:
    with open(path) as f:
        data = json.load(f)
    data["captured_at"] = datetime.fromisoformat(data["captured_at"])
    return InstagramSnapshot(**data)


def linkedin_configured() -> bool:
    return bool(os.environ.get("LINKEDIN_ACCESS_TOKEN")) and \
           bool(os.environ.get("LINKEDIN_PERSON_URN"))

def image_configured() -> bool:
    return bool(os.environ.get("HF_TOKEN"))


async def main() -> None:
    print("=" * 50)
    print("Social Intelligence Agent -- Full Pipeline")
    print("=" * 50)

    raw = load_snapshot("data/snapshots/june_2026.json")
    snapshot = InstagramNormalizer().normalize(raw)
    print(f"Snapshot:  engagement={snapshot.engagement_rate:.2%} | conversion={snapshot.conversion_rate:.2%}")

    print("Analyzing...")
    report = AnalyticsService().analyze(snapshot)
    print(f"Priority:  {report.top_priority}\n")

    content_agent = ContentAgent()
    review_agent  = ReviewAgent()
    bot           = ApprovalBot()

    attempt = 0
    while True:
        attempt += 1
        print(f"Generating draft (attempt {attempt})...")
        draft = content_agent.generate(report, platform="linkedin")
        print(f"Words: {len(draft.split())}\n")

        result = review_agent.review(draft, platform="linkedin")
        print(f"Review: {result.verdict}")

        if result.verdict == "REJECT":
            for issue in result.issues:
                print(f"  ! {issue}")
            if attempt >= 3:
                print("3 attempts reached. Stopping.")
                return
            print("Regenerating...\n")
            continue

        print("\n" + "-" * 50)
        print("DRAFT")
        print("-" * 50)
        print(draft)
        print("-" * 50)

        if result.issues:
            print("\nMinor issues (sending anyway):")
            for issue in result.issues:
                print(f"  ! {issue}")

        image_path = None
        if image_configured():
            try:
                print("Generating infographic...")
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    image_path = await loop.run_in_executor(
                        pool, InfographicAgent().generate, draft
                    )
            except Exception as e:
                print(f"Infographic failed ({e.__class__.__name__}: {str(e)[:80]})")
                print("Continuing without image.")

        print("\nSending to Telegram...")
        decision, post_id = await bot.send_for_approval(draft)
        print(f"Decision: {decision.upper()}")

        if decision == "approve":
            if linkedin_configured():
                print("Publishing to LinkedIn...")
                try:
                    pub_result = LinkedInPublisher().post(draft, image_path=image_path)
                    update_platform_post_id(post_id, pub_result.platform_post_id)
                    print(f"Live on LinkedIn: {pub_result.platform_post_id}")
                except PublishError as e:
                    print(f"LinkedIn publish failed: {e}")
                    print("PostRecord saved without platform_post_id.")
            else:
                print("LinkedIn not configured — PostRecord saved, post manually.")
            break
        elif decision == "reject":
            print("Rejected. Stopping.")
            break
        elif decision == "redraft":
            print("Redrafting...\n")
            continue


if __name__ == "__main__":
    asyncio.run(main())
