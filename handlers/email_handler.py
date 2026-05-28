import logging
from datetime import datetime
from telegram.ext import ContextTypes

from services.gmail_service import get_unread_receipt_emails, mark_as_read
from services.pdf_service import pdf_to_image_bytes
from services.ocr_service import extract_text
from services.parser_service import parse_receipt, format_for_telegram
from services.email_parser_service import parse_html_receipt
from services.supabase_service import upload_receipt, log_receipt

logger = logging.getLogger(__name__)


async def poll_emails(context: ContextTypes.DEFAULT_TYPE):
    """
    Called every 5 minutes by the job queue.
    Handles both attachment-based and HTML-body receipts.
    """
    import os
    user_id = int(os.getenv("TELEGRAM_USER_ID", 0))
    if not user_id:
        logger.error("TELEGRAM_USER_ID not set in environment variables")
        return

    try:
        emails = get_unread_receipt_emails()
        if not emails:
            return

        logger.info(f"Found {len(emails)} unread email(s)")

        for email in emails:
            processed = False

            # ── Path 1: Attachment (image or PDF) ────────────────────────────
            for attachment in email["attachments"]:
                filename = attachment["filename"]
                mime_type = attachment["mime_type"]
                file_bytes = attachment["data"]

                if mime_type == "application/pdf":
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📧 Email from *{email['sender']}*\n🔄 Converting PDF...",
                        parse_mode="Markdown"
                    )
                    file_bytes = pdf_to_image_bytes(file_bytes)
                    if not file_bytes:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"❌ Could not convert PDF from {email['sender']}"
                        )
                        continue
                    mime_type = "image/jpeg"
                    filename = filename.replace(".pdf", ".jpg")

                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                save_filename = f"{user_id}_email_{timestamp}_{filename}"

                storage_path = upload_receipt(file_bytes, save_filename, mime_type)
                extracted_text = extract_text(file_bytes)
                parsed = parse_receipt(extracted_text)
                log_receipt(user_id, save_filename, storage_path, parsed)

                summary = format_for_telegram(parsed)
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📧 *Receipt from email!*\n_From: {email['sender']}_\n\n{summary}",
                    parse_mode="Markdown"
                )
                processed = True

            # ── Path 2: HTML body (e.g. McDonald's) ──────────────────────────
            if not processed and email.get("html_body"):
                parsed = parse_html_receipt(
                    email["html_body"],
                    email["sender"],
                    email["subject"]
                )

                if parsed:
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    save_filename = f"{user_id}_email_{timestamp}_html_receipt.txt"

                    # Save the HTML as text to Supabase for reference
                    log_receipt(user_id, save_filename, "html_email", parsed)

                    summary = format_for_telegram(parsed)
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📧 *Receipt from email!*\n_From: {email['sender']}_\n\n{summary}",
                        parse_mode="Markdown"
                    )
                    processed = True

            if not processed:
                logger.info(f"Skipped email '{email['subject']}' — not a receipt")

            # Always mark as read
            mark_as_read(email["id"])

    except Exception as e:
        logger.error(f"Email polling failed: {e}")