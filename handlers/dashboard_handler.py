import logging
from telegram import Update
from telegram.ext import ContextTypes

from services.supabase_service import get_spend_summary, get_recent_receipts

logger = logging.getLogger(__name__)


async def handle_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        summary = get_spend_summary(user_id)

        today = summary["today"]
        week = summary["week"]
        month = summary["month"]
        count = summary["receipt_count"]
        top_merchants = summary["top_merchants"]

        merchants_text = ""
        if top_merchants:
            for i, (merchant, total) in enumerate(top_merchants, 1):
                merchants_text += f"  {i}. {merchant} — ${total:.2f}\n"
        else:
            merchants_text = "  No data yet\n"

        msg = (
            "📊 *Receipt Dashboard*\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💸 *Spending Summary*\n"
            f"  Today:      ${today:.2f}\n"
            f"  This week:  ${week:.2f}\n"
            f"  This month: ${month:.2f}\n\n"
            f"🧾 Receipts this month: {count}\n\n"
            "🏪 *Top Merchants (this month)*\n"
            f"{merchants_text}\n"
            "_Use /recent to see your latest receipts_"
        )

        await update.message.reply_text(msg, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        await update.message.reply_text("❌ Could not load dashboard. Please try again.")


async def handle_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    try:
        receipts = get_recent_receipts(user_id, limit=5)

        if not receipts:
            await update.message.reply_text("No receipts found yet. Send a photo or file to get started!")
            return

        lines = ["🧾 *Recent Receipts*\n━━━━━━━━━━━━━━━━━━━━\n"]
        for r in receipts:
            merchant = r.get("merchant") or "Unknown"
            amount = r.get("total_amount")
            date = r.get("receipt_date") or r.get("scanned_at", "")[:10]
            amount_str = f"${float(amount):.2f}" if amount is not None else "N/A"
            lines.append(f"• {date}  *{merchant}*  —  {amount_str}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Recent receipts error: {e}")
        await update.message.reply_text("❌ Could not load recent receipts. Please try again.")


async def handle_spend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /spend [today|week|month] — defaults to month."""
    user_id = update.message.from_user.id
    args = context.args
    period = args[0].lower() if args else "month"

    if period not in ("today", "week", "month"):
        await update.message.reply_text(
            "Usage: `/spend today`, `/spend week`, or `/spend month`",
            parse_mode="Markdown"
        )
        return

    try:
        summary = get_spend_summary(user_id)

        amount = summary.get(period, 0.0)
        label = {"today": "Today", "week": "This Week", "month": "This Month"}[period]

        await update.message.reply_text(
            f"💸 *{label}'s Spend*\n\n${amount:.2f}",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Spend command error: {e}")
        await update.message.reply_text("❌ Could not fetch spend. Please try again.")
