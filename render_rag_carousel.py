"""Render and send the RAG explanation carousel — 3 hardcoded slides.

Content is fixed (no LLM call) — rendered directly from structured data.
"""

import asyncio
import concurrent.futures
from dotenv import load_dotenv

from schemas.visual_block import Carousel, VisualBlock
from renderers.block_renderer import BlockRenderer
from bots.telegram_approval import ApprovalBot

load_dotenv()


# ── Hardcoded carousel ─────────────────────────────────────────────────────
CAROUSEL = Carousel(
    topic="RAG PIPELINE",
    hero="RAG EXPLAINED",
    blocks=[
        VisualBlock(
            type="what",
            title="What is RAG?",
            topic="RAG PIPELINE",
            icon="brain",
            order=0,
            point_items=[
                {
                    "label": "RAG = Retrieval-Augmented Generation",
                    "detail": "A pattern that gives an LLM access to external knowledge before answering.",
                    "icon": "brain",
                },
                {
                    "label": "Without RAG",
                    "detail": "User → LLM → Answer. Model only uses training data. Cannot access private or fresh info.",
                    "icon": "agent",
                },
                {
                    "label": "With RAG",
                    "detail": "User → Retriever → Relevant Docs → LLM → Answer. Model gets accurate, up-to-date context.",
                    "icon": "search",
                },
                {
                    "label": "Why it exists",
                    "detail": "LLMs hallucinate and have no access to your company docs, latest news, or private databases.",
                    "icon": "check",
                },
            ],
        ),
        VisualBlock(
            type="flow",
            title="How RAG Works — 5 Steps",
            topic="RAG PIPELINE",
            icon="flow",
            order=1,
            flow=[
                "Document — Load your PDFs, Notion pages, databases",
                "Chunk — Split into 500-token pieces with overlap",
                "Embed — Convert each chunk into a vector (numbers)",
                "Store — Save vectors in a vector database (Pinecone, Qdrant)",
                "Retrieve — Query → similarity search → top-k chunks → LLM",
            ],
        ),
        VisualBlock(
            type="what",
            title="Where RAG Sits in an Agent",
            topic="RAG PIPELINE",
            icon="agent",
            order=2,
            point_items=[
                {
                    "label": "Memory",
                    "detail": "Stores past interactions — what happened before in the conversation.",
                    "icon": "memory",
                },
                {
                    "label": "Tools",
                    "detail": "APIs and functions the agent can call — search, calculator, code runner.",
                    "icon": "api",
                },
                {
                    "label": "RAG — Knowledge Layer",
                    "detail": "Retrieves from your PDFs, Notion pages, databases, and company docs.",
                    "icon": "database",
                },
                {
                    "label": "Key rule",
                    "detail": "Resource = Knowledge.  RAG = Access Method.  Agent = Decision Maker.",
                    "icon": "brain",
                },
            ],
        ),
    ],
)


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


async def main() -> None:
    _clear_telegram_session()

    print("Rendering 3 RAG slides — light_minimal style...")
    renderer = BlockRenderer()

    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        paths = await loop.run_in_executor(
            pool,
            lambda: renderer.render_carousel(
                CAROUSEL.blocks,
                platform="linkedin",
                style="light_minimal",
            ),
        )

    print(f"Rendered: {len(paths)} slides")
    for p in paths:
        print(f"  {p}")

    print("\nSending to Telegram...")
    bot = ApprovalBot()
    decision, post_id, suggestion = await bot.send_carousel_for_approval(
        paths,
        topic="RAG Pipeline Explained",
        platform="linkedin",
    )

    print(f"\nDecision  : {decision.upper()}")
    if suggestion:
        print(f"Suggestion: {suggestion}")

    if decision == "approve":
        print("Approved — ready for publishing.")
    elif decision == "redraft":
        print(f"Redraft requested{f': {suggestion}' if suggestion else ''}.")
    else:
        print("Rejected.")


if __name__ == "__main__":
    asyncio.run(main())
