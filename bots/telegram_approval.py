"""Telegram approval bot — sends image + post text, waits for human decision.

Buttons: Approve | Reject | Redraft
- Approve  → saves PostRecord, returns ('approve', post_id, None)
- Reject   → returns ('reject', post_id, None)
- Redraft  → asks for optional suggestion → returns ('redraft', post_id, suggestion_or_None)
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from telegram import InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from telegram.request import HTTPXRequest

from schemas.engagement import PostRecord
from memory.store import init_db, save_post_record


class ApprovalBot:

    def __init__(self) -> None:
        self._token = os.environ["TELEGRAM_BOT_TOKEN"]
        self._chat_id = os.environ["TELEGRAM_CHAT_ID"]
        self._decision: str | None = None
        self._suggestion: str | None = None
        self._waiting_for_suggestion: bool = False
        self._event = asyncio.Event()
        self._post_id: str | None = None
        self._platform: str = "linkedin"
        self._generated: str | None = None
        self._approval_is_text: bool = False   # True for carousel (text msg), False for photo
        init_db()

    def _approval_keyboard(self, post_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Approve",  callback_data=f"approve:{post_id}"),
            InlineKeyboardButton("Reject",   callback_data=f"reject:{post_id}"),
            InlineKeyboardButton("Redraft",  callback_data=f"redraft:{post_id}"),
        ]])

    def _skip_keyboard(self, post_id: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("Skip — regenerate as-is", callback_data=f"skip:{post_id}"),
        ]])

    async def _handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        query = update.callback_query
        await query.answer()
        action, post_id = query.data.split(":", 1)

        if post_id != self._post_id:
            return

        async def _edit(text: str, reply_markup=None) -> None:
            if self._approval_is_text:
                await query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await query.edit_message_caption(text, reply_markup=reply_markup)

        if action == "approve":
            record = PostRecord(
                post_id=post_id,
                platform=self._platform,
                generated_content=self._generated,
                approved_content=self._generated,
                posted_at=datetime.now(timezone.utc),
            )
            save_post_record(record)
            await _edit(f"Approved. Post ID: {post_id}")
            self._decision = "approve"
            self._event.set()

        elif action == "reject":
            await _edit("Rejected.")
            self._decision = "reject"
            self._event.set()

        elif action == "redraft":
            self._waiting_for_suggestion = True
            await _edit(
                "Redraft requested.\n\n"
                "Any suggestions to improve the post? (optional)\n"
                "Type a message — or press Skip to regenerate as-is.",
                reply_markup=self._skip_keyboard(post_id),
            )

        elif action == "skip":
            self._suggestion = None
            self._decision = "redraft"
            self._waiting_for_suggestion = False
            await _edit("Regenerating without additional suggestions...")
            self._event.set()

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._waiting_for_suggestion:
            return
        if str(update.effective_chat.id) != str(self._chat_id):
            return

        self._suggestion = update.message.text.strip()
        self._decision = "redraft"
        self._waiting_for_suggestion = False

        await update.message.reply_text(
            f"Got it. Regenerating with your suggestion:\n\"{self._suggestion}\""
        )
        self._event.set()

    async def send_for_approval(
        self, post_text: str, image_path: str | None = None, platform: str = "linkedin"
    ) -> tuple[str, str, str | None]:
        """Send image + post to Telegram. Returns (decision, post_id, suggestion)."""
        self._post_id = str(uuid.uuid4())[:8]
        self._platform = platform
        self._generated = post_text
        self._decision = None
        self._suggestion = None
        self._waiting_for_suggestion = False
        self._approval_is_text = False   # single image approval is a photo caption
        self._event.clear()

        request = HTTPXRequest(connect_timeout=60, read_timeout=60, write_timeout=60)
        app = (
            Application.builder()
            .token(self._token)
            .request(request)
            .build()
        )
        app.add_handler(CallbackQueryHandler(self._handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        word_count = len(post_text.split())
        caption = f"DRAFT ({word_count} words)\n\n{post_text}"
        if len(caption) > 1024:
            caption = caption[:1020] + "..."

        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        for attempt in range(3):
            try:
                if image_path and Path(image_path).exists():
                    with open(image_path, "rb") as img:
                        await app.bot.send_photo(
                            chat_id=self._chat_id,
                            photo=img,
                            caption=caption,
                            reply_markup=self._approval_keyboard(self._post_id),
                            read_timeout=60,
                            write_timeout=60,
                            connect_timeout=60,
                        )
                else:
                    await app.bot.send_message(
                        chat_id=self._chat_id,
                        text=caption,
                        reply_markup=self._approval_keyboard(self._post_id),
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30,
                    )
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(3)

        await self._event.wait()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

        return self._decision, self._post_id, self._suggestion

    async def send_carousel_for_approval(
        self,
        slide_paths: list[str],
        topic: str,
        platform: str = "linkedin",
    ) -> tuple[str, str, str | None]:
        """Send N carousel slides as a Telegram album, then approval buttons.

        Returns (decision, post_id, suggestion).
        decision: 'approve' | 'reject' | 'redraft'
        """
        self._post_id = str(uuid.uuid4())[:8]
        self._platform = platform
        self._generated = topic
        self._decision = None
        self._suggestion = None
        self._waiting_for_suggestion = False
        self._approval_is_text = True   # carousel approval is a text message
        self._event.clear()

        request = HTTPXRequest(connect_timeout=60, read_timeout=60, write_timeout=60)
        app = (
            Application.builder()
            .token(self._token)
            .request(request)
            .build()
        )
        app.add_handler(CallbackQueryHandler(self._handle_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

        valid_paths = [p for p in slide_paths if Path(p).exists()]

        for attempt in range(3):
            try:
                # ── Send slides as album (max 10 per Telegram group) ──
                for batch_start in range(0, len(valid_paths), 10):
                    batch = valid_paths[batch_start:batch_start + 10]
                    media_group = []
                    for i, path in enumerate(batch):
                        slide_num = batch_start + i + 1
                        caption = (
                            f"Slide {slide_num}/{len(valid_paths)} — {topic}"
                            if i == 0 else ""
                        )
                        with open(path, "rb") as f:
                            media_group.append(InputMediaPhoto(
                                media=f.read(),
                                caption=caption,
                            ))
                    await app.bot.send_media_group(
                        chat_id=self._chat_id,
                        media=media_group,
                        read_timeout=60,
                        write_timeout=60,
                        connect_timeout=60,
                    )

                # ── Approval message after the album ──────────────────
                await app.bot.send_message(
                    chat_id=self._chat_id,
                    text=(
                        f"Carousel ready — {len(valid_paths)} slides\n"
                        f"Topic: {topic}\nPlatform: {platform}"
                    ),
                    reply_markup=self._approval_keyboard(self._post_id),
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30,
                )
                break
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(3)

        await self._event.wait()
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

        return self._decision, self._post_id, self._suggestion
