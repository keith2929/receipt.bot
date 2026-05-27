import logging
import asyncio
import threading
import os
from dotenv import load_dotenv
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters

from handlers.receipt_handler import handle_receipt
from handlers.usage_handler import handle_usage

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ── Minimal Flask server so Render keeps the service alive ─────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Bot is running.", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# ── Telegram bot ───────────────────────────────────────────────────────────────
async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not found in .env")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.Document.ALL, handle_receipt))
    app.add_handler(MessageHandler(filters.PHOTO, handle_receipt))
    app.add_handler(CommandHandler("usage", handle_usage))

    print("Bot is running...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()  # Run forever

if __name__ == "__main__":
    # Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Bot runs with its own event loop
    asyncio.run(main())