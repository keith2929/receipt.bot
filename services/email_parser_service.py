import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_html_receipt(html: str, sender: str, subject: str) -> dict | None:
    """
    Parse receipt data from an HTML email body.
    Returns a parsed dict in the same format as parse_receipt(),
    or None if the email doesn't look like a receipt.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")

    # Detect if this looks like a receipt at all
    receipt_keywords = ["total", "order", "payment", "receipt", "amount", "invoice"]
    if not any(kw in text.lower() for kw in receipt_keywords):
        return None

    # ── McDonald's format ─────────────────────────────────────────────────────
    if "mcdonalds" in sender.lower() or "mcdonald" in text.lower():
        return _parse_mcdonalds(soup, text)

    # ── Generic HTML receipt fallback ─────────────────────────────────────────
    return _parse_generic(soup, text, sender)


def _parse_mcdonalds(soup: BeautifulSoup, text: str) -> dict:
    """Parse McDonald's email receipt format."""
    items = []

    # Extract items from the order table
    rows = soup.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 3:
            qty_text = cells[0].get_text(strip=True)
            item_text = cells[1].get_text(strip=True)
            price_text = cells[2].get_text(strip=True)

            # Skip header rows, empty rows, and modifier rows (no price)
            price_match = re.search(r"SGD\s*([\d.]+)", price_text)
            qty_match = re.match(r"^\d+$", qty_text)

            if qty_match and price_match and item_text:
                items.append({
                    "name": item_text.strip(),
                    "price": float(price_match.group(1))
                })

    # Extract GST
    gst_match = re.search(r"SGD\s*([\d.]+)", 
        "\n".join([r.get_text() for r in soup.find_all("tr") 
                   if "GST" in r.get_text() and "SGD" in r.get_text()]))
    if gst_match:
        items.append({"name": "GST (not separately charged)", 
                      "price": float(gst_match.group(1))})

    # Extract total
    total = 0.0
    total_match = re.search(r"Total.*?SGD\s*([\d.]+)", text, re.IGNORECASE | re.DOTALL)
    if total_match:
        total = float(total_match.group(1))

    # Extract date
    from datetime import datetime
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

    # Extract restaurant name
    merchant = "McDonald's"
    restaurant_match = re.search(r"Restaurant Name.*?\n.*?(McDonald's[^\n]+)", text)
    if restaurant_match:
        merchant = restaurant_match.group(1).strip()

    # Extract location/address
    location = "Unknown"
    address_match = re.search(r"Address.*?\n(.*?Singapore\s*\d{6})", text, re.DOTALL)
    if address_match:
        location = " ".join(address_match.group(1).split())

    # Extract payment
    payment = "Unknown"
    if re.search(r"visa", text, re.IGNORECASE):
        payment = "Visa"
    elif re.search(r"mastercard", text, re.IGNORECASE):
        payment = "Mastercard"
    elif re.search(r"paynow", text, re.IGNORECASE):
        payment = "PayNow"

    return {
        "merchant": merchant,
        "location": location,
        "receipt_date": receipt_date,
        "total_amount": total,
        "original_currency": "SGD",
        "payment_method": payment,
        "items": items,
    }


def _parse_generic(soup: BeautifulSoup, text: str, sender: str) -> dict:
    """Generic fallback parser for unknown HTML receipt formats."""
    from datetime import datetime

    # Try to extract total
    total = 0.0
    total_match = re.search(
        r"(?:total|amount due|grand total)[^\d]*([\d,]+\.\d{2})", 
        text, re.IGNORECASE
    )
    if total_match:
        total = float(total_match.group(1).replace(",", ""))

    # Try to extract date
    receipt_date = None
    date_match = re.search(r"(\d{2}[/-]\d{2}[/-]\d{2,4})\s+(\d{2}:\d{2})", text)
    if date_match:
        try:
            receipt_date = datetime.strptime(
                f"{date_match.group(1)} {date_match.group(2)}", "%d/%m/%Y %H:%M"
            ).isoformat()
        except ValueError:
            pass

    # Merchant from sender email domain
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