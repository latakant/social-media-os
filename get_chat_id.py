"""Run this once to get your correct Telegram chat ID.

1. Run: python get_chat_id.py
2. Send any message to your bot on Telegram
3. Copy the chat ID printed here into .env
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

_got_id = asyncio.Event()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    user = update.effective_user.first_name
    print(f"\nGot message from: {user}")
    print(f"Your chat ID is:  {chat_id}")
    print(f"\nAdd to .env:\nTELEGRAM_CHAT_ID={chat_id}")
    await update.message.reply_text(f"Chat ID: {chat_id}")
    _got_id.set()


async def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    print("Waiting for a message from you on Telegram...")
    print("Open your bot and send any message (e.g. 'hello')\n")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    await _got_id.wait()

    await app.updater.stop()
    await app.stop()
    await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
