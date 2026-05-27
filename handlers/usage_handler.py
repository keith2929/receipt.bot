import logging
from telegram import Update
from telegram.ext import ContextTypes

from services.supabase_service import get_monthly_usage

logger = logging.getLogger(__name__)

MONTHLY_LIMIT = 1000

async def handle_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        used = get_monthly_usage(user_id)
        remaining = MONTHLY_LIMIT - used

        await update.message.reply_text(
            f"📊 *Google Vision Usage — This Month*\n\n"
            f"✅ Scanned: {used}\n"
            f"🔲 Remaining: {remaining}\n"
            f"📦 Monthly limit: {MONTHLY_LIMIT}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Failed to fetch usage: {e}")
        await update.message.reply_text("❌ Could not fetch usage. Please try again.")