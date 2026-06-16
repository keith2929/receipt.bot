import os
import logging
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME", "receipts")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_receipt(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """Upload receipt bytes to Supabase Storage. Returns the storage path."""
    storage_path = filename
    response = supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": mime_type, "upsert": "false"}
    )
    logger.info(f"Supabase upload response: {response}")
    return storage_path


def log_receipt(user_id: int, filename: str, storage_path: str, parsed: dict):
    """Log a receipt scan to the receipts table including parsed data."""
    import json
    response = supabase.table("receipts").insert({
        "user_id": user_id,
        "filename": filename,
        "storage_path": storage_path,
        "scanned_at": datetime.utcnow().isoformat(),
        "merchant": parsed.get("merchant"),
        "location": parsed.get("location"),
        "receipt_date": parsed.get("receipt_date"),
        "total_amount": parsed.get("total_amount"),
        "payment_method": parsed.get("payment_method"),
        "items": json.dumps(parsed.get("items", [])),
    }).execute()
    logger.info(f"Logged receipt to DB: {response}")


def get_monthly_usage(user_id: int) -> int:
    """Count how many receipts the user has scanned this calendar month."""
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1).isoformat()
    response = supabase.table("receipts") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .gte("scanned_at", month_start) \
        .execute()
    return response.count or 0


def get_spend_summary(user_id: int) -> dict:
    """Return spend totals for today, this week, and this month, plus top merchants."""
    now = datetime.utcnow()

    today_start = datetime(now.year, now.month, now.day).isoformat()
    week_day = now.weekday()  # Monday=0
    week_start = datetime(now.year, now.month, now.day - week_day).isoformat()
    month_start = datetime(now.year, now.month, 1).isoformat()

    response = supabase.table("receipts") \
        .select("total_amount, merchant, receipt_date, scanned_at") \
        .eq("user_id", user_id) \
        .gte("scanned_at", month_start) \
        .execute()

    rows = response.data or []

    today_total = 0.0
    week_total = 0.0
    month_total = 0.0
    merchant_totals: dict = {}
    receipt_count = len(rows)

    for row in rows:
        amount = float(row.get("total_amount") or 0)
        scanned_at = row.get("scanned_at", "")
        merchant = row.get("merchant") or "Unknown"

        month_total += amount

        if scanned_at >= week_start:
            week_total += amount

        if scanned_at >= today_start:
            today_total += amount

        merchant_totals[merchant] = merchant_totals.get(merchant, 0.0) + amount

    top_merchants = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "today": today_total,
        "week": week_total,
        "month": month_total,
        "receipt_count": receipt_count,
        "top_merchants": top_merchants,
    }


def get_recent_receipts(user_id: int, limit: int = 5) -> list:
    """Return the most recent receipts for the user."""
    response = supabase.table("receipts") \
        .select("merchant, total_amount, receipt_date, scanned_at") \
        .eq("user_id", user_id) \
        .order("scanned_at", desc=True) \
        .limit(limit) \
        .execute()
    return response.data or []