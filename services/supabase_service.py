import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialise Supabase client once at import time
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME", "receipts")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_receipt(file_bytes: bytes, filename: str, mime_type: str) -> str:
    """
    Upload receipt bytes to Supabase Storage.
    Returns the file path in the bucket (not a public URL since bucket is private).
    """
    storage_path = filename

    response = supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": mime_type, "upsert": "false"}
    )

    logger.info(f"Supabase upload response: {response}")

    # Return the storage path — you can generate a signed URL later if needed
    return storage_path
