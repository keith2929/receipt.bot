import logging
from dotenv import load_dotenv
import os
from telegram.ext import ApplicationBuilder, MessageHandler, filters

from handlers.receipt_handler import handle_receipt

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
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_receipt))

    # Inform user if they send a compressed photo instead of a file
    app.add_handler(MessageHandler(filters.PHOTO, handle_wrong_format))

    print("Bot is running...")
    app.run_polling()

async def handle_wrong_format(update, context):
    await update.message.reply_text(
        "⚠️ Please send your receipt as a *File*, not a Photo.\n\n"
        "Tap 📎 → File when attaching — this preserves full quality for better scanning later.",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    main()