import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── Receipt detection ──────────────────────────────────────────────────────────

RECEIPT_SUBJECTS = [
    "receipt", "order", "payment", "invoice", "purchase",
    "confirmation", "transaction", "your order"
]

RECEIPT_SENDERS = [
    "mcdonalds.com", "mcdonald", "grab", "foodpanda", "shopee",
    "lazada", "amazon", "ntuc", "fairprice", "kfc", "burgerking",
    "starbucks", "toast", "deliveroo", "airbnb", "booking.com"
]

def is_receipt_email(sender: str, subject: str) -> bool:
    """Check if email looks like a receipt before trying to parse it."""
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    sender_match = any(s in sender_lower for s in RECEIPT_SENDERS)
    subject_match = any(s in subject_lower for s in RECEIPT_SUBJECTS)
    return sender_match or subject_match


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_html_receipt(html: str, sender: str, subject: str) -> dict | None:
    """
    Parse receipt data from an HTML email body.
    Returns a parsed dict or None if email doesn't look like a receipt.
    """
    if not is_receipt_email(sender, subject):
        logger.info(f"Skipping non-receipt email: {subject} from {sender}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    if "mcdonalds.com" in sender.lower() or "mcdonald" in subject.lower():
        return _parse_mcdonalds(soup)

    return _parse_generic(soup, sender)


# ── McDonald's parser ──────────────────────────────────────────────────────────

def _parse_mcdonalds(soup: BeautifulSoup) -> dict:
    from datetime import datetime

    text = soup.get_text(separator="\n")

    # ── Merchant & location ───────────────────────────────────────────────────
    merchant = "McDonald's"
    location = "Unknown"

    all_rows = soup.find_all("tr")
    for row in all_rows:
        cells = row.find_all(["td", "th"])
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if "Restaurant Name" in label:
                merchant = value
            if "Address" in label:
                location = " ".join(value.split())

    # ── Date ─────────────────────────────────────────────────────────────────
    receipt_date = None
    date_match = re.search(r"(\d{2}/\d{2}/\d{2,4})\s+(\d{2}:\d{2})", text)
    if date_match:
        date_str = f"{date_match.group(1)} {date_match.group(2)}"
        for fmt in ["%d/%m/%y %H:%M", "%d/%m/%Y %H:%M"]:
            try:
                receipt_date = datetime.strptime(date_str, fmt).isoformat()
                break
            except ValueError:
                continue

    # ── Items ─────────────────────────────────────────────────────────────────
    # Only include top-level items (those with a price in SGD)
    items = []
    for row in all_rows:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        qty_text = cells[0].get_text(strip=True)
        item_text = cells[1].get_text(strip=True)
        price_text = cells[2].get_text(strip=True)

        price_match = re.search(r"SGD\s*([\d.]+)", price_text)
        if not price_match:
            continue  # Skip sub-items and rows without price

        # Clean item name — remove leading numbers and whitespace
        item_name = re.sub(r"^\s*\d+\s*", "", item_text).strip()
        if not item_name:
            continue

        items.append({
            "name": item_name,
            "price": float(price_match.group(1))
        })

    # ── GST ───────────────────────────────────────────────────────────────────
    gst_match = re.search(r"GST Inclusive.*?SGD\s*([\d.]+)", text, re.DOTALL)
    if not gst_match:
        gst_match = re.search(r"SGD\s*([\d.]+)(?=.*GST)", text)
    if gst_match:
        items.append({
            "name": "GST (not separately charged)",
            "price": float(gst_match.group(1))
        })

    # ── Total ─────────────────────────────────────────────────────────────────
    total = 0.0
    total_match = re.search(r"Total:.*?SGD\s*([\d.]+)", text, re.DOTALL)
    if total_match:
        total = float(total_match.group(1))

    # ── Payment ───────────────────────────────────────────────────────────────
    payment = "Unknown"
    card_match = re.search(r"Card Issuer.*?\n.*?(\w+)", text)
    if card_match:
        payment = card_match.group(1).strip()

    return {
        "merchant": merchant,
        "location": location,
        "receipt_date": receipt_date,
        "total_amount": total,
        "original_currency": "SGD",
        "payment_method": payment,
        "items": items,
    }


# ── Generic fallback ───────────────────────────────────────────────────────────

def _parse_generic(soup: BeautifulSoup, sender: str) -> dict:
    from datetime import datetime

    text = soup.get_text(separator="\n")

    total = 0.0
    total_match = re.search(
        r"(?:total|amount due|grand total)[^\d]*([\d,]+\.\d{2})",
        text, re.IGNORECASE
    )
    if total_match:
        total = float(total_match.group(1).replace(",", ""))

    receipt_date = None
    date_match = re.search(r"(\d{2}[/-]\d{2}[/-]\d{2,4})\s+(\d{2}:\d{2})", text)
    if date_match:
        try:
            receipt_date = datetime.strptime(
                f"{date_match.group(1)} {date_match.group(2)}", "%d/%m/%Y %H:%M"
            ).isoformat()
        except ValueError:
            pass

    merchant = re.sub(r"[<>].*", "", sender).strip()

    return {
        "merchant": merchant,
        "location": "Unknown",
        "receipt_date": receipt_date,
        "total_amount": total,
        "original_currency": "SGD",
        "payment_method": "Unknown",
        "items": [],
    }