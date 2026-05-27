import logging
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters

from handlers.receipt_handler import handle_receipt
from handlers.usage_handler import handle_usage

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not found in .env")

    app = ApplicationBuilder().token(token).build()

    # Handle documents (files sent as attachments, not compressed photos)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_receipt))

    # Handle compressed photos with a warning
    app.add_handler(MessageHandler(filters.PHOTO, handle_wrong_format))

    # /usage command
    app.add_handler(CommandHandler("usage", handle_usage))

    print("Bot is running...")
    app.run_polling()

async def handle_wrong_format(update, context):
    await update.message.reply_text(
        "⚠️ Please send your receipt as a *File*, not a Photo.\n\n"
        "Tap 📎 → File when attaching — this preserves full quality for better scanning.",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    main()