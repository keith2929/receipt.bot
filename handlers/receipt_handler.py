import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from services.supabase_service import upload_receipt
from services.ocr_service import extract_text

logger = logging.getLogger(__name__)

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    user_id = update.message.from_user.id

    await update.message.reply_text("📥 Got it! Uploading and scanning your receipt...")

    try:
        # Download file from Telegram into memory
        file = await context.bot.get_file(doc.file_id)
        file_bytes = bytes(await file.download_as_bytearray())

        # Generate a unique filename: userID_timestamp_originalname
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_name = doc.file_name or "receipt"
        filename = f"{user_id}_{timestamp}_{original_name}"

        # Upload to Supabase
        storage_path = upload_receipt(file_bytes, filename, doc.mime_type or "image/jpeg")
        logger.info(f"Uploaded receipt for user {user_id}: {filename}")

        # Run OCR
        await update.message.reply_text("🔍 Running OCR scan...")
        extracted_text = extract_text(file_bytes)

        # Send results back
        await update.message.reply_text(
            f"✅ Receipt saved!\n\n"
            f"📄 *Extracted text:*\n```\n{extracted_text}\n```",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Failed to process receipt: {e}")
        await update.message.reply_text(
            "❌ Something went wrong processing your receipt. Please try again."
        )