import os
import json
import base64
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _make_gmail_client():
    """Create Gmail client from env var (Render) or local file (local dev)."""
    token_json = os.getenv("GMAIL_TOKEN_JSON")
    if token_json:
        creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    else:
        with open("credentials/gmail_token.json", "r") as f:
            creds = Credentials.from_authorized_user_info(json.load(f), SCOPES)
    return build("gmail", "v1", credentials=creds)


def get_unread_receipt_emails() -> list[dict]:
    """
    Fetch unread emails with attachments from Gmail inbox.
    Returns list of dicts with subject, sender, and attachments.
    """
    service = _make_gmail_client()
    results = service.users().messages().list(
        userId="me",
        q="is:unread has:attachment"
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg_data["payload"]["headers"]}
        subject = headers.get("Subject", "No subject")
        sender = headers.get("From", "Unknown sender")

        attachments = []
        parts = msg_data["payload"].get("parts", [])

        for part in parts:
            mime_type = part.get("mimeType", "")
            filename = part.get("filename", "")

            if not filename:
                continue

            # Only process images and PDFs
            if not any(mime_type.startswith(t) for t in ["image/", "application/pdf"]):
                continue

            attachment_id = part["body"].get("attachmentId")
            if not attachment_id:
                continue

            att_data = service.users().messages().attachments().get(
                userId="me",
                messageId=msg["id"],
                id=attachment_id
            ).execute()

            file_bytes = base64.urlsafe_b64decode(att_data["data"])
            attachments.append({
                "filename": filename,
                "mime_type": mime_type,
                "data": file_bytes
            })

        if attachments:
            emails.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender,
                "attachments": attachments
            })

    return emails


def mark_as_read(message_id: str):
    """Mark an email as read after processing."""
    service = _make_gmail_client()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()
    logger.info(f"Marked email {message_id} as read")