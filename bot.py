import logging
import asyncio
import threading
import os
from dotenv import load_dotenv
from flask import Flask
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters

from handlers.receipt_handler import handle_receipt
from handlers.usage_handler import handle_usage
from handlers.email_handler import poll_emails
from handlers.dashboard_handler import handle_dashboard, handle_recent, handle_spend

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
    app.add_handler(CommandHandler("dashboard", handle_dashboard))
    app.add_handler(CommandHandler("recent", handle_recent))
    app.add_handler(CommandHandler("spend", handle_spend))

    # Poll Gmail every 5 minutes
    app.job_queue.run_repeating(poll_emails, interval=300, first=10)

    print("Bot is running...")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(main())