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