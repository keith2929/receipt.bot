import re
import logging
import requests

logger = logging.getLogger(__name__)

# ── Currency conversion ────────────────────────────────────────────────────────

CURRENCY_SYMBOLS = {
    "USD": ["USD", "US$", "U.S.$"],
    "MYR": ["MYR", "RM"],
    "IDR": ["IDR", "Rp"],
    "THB": ["THB", "฿"],
    "JPY": ["JPY", "¥", "円"],
    "AUD": ["AUD", "A$"],
    "GBP": ["GBP", "£"],
    "EUR": ["EUR", "€"],
    "HKD": ["HKD", "HK$"],
    "SGD": ["SGD", "S$", "SGD$"],
}

def detect_currency(text: str) -> str:
    """
    Detect currency from OCR text. Defaults to SGD.
    Uses whole-word matching to avoid false positives from card terminal data.
    """
    # Only match explicit 3-letter currency codes as whole words
    explicit_codes = ["USD", "MYR", "IDR", "THB", "JPY", "AUD", "GBP", "EUR", "HKD"]
    for code in explicit_codes:
        if re.search(rf'\b{code}\b', text, re.IGNORECASE):
            return code

    # Match unambiguous symbols only (not short ones like Rp that cause false positives)
    safe_symbols = {
        "THB": ["฿"],
        "JPY": ["¥", "円"],
        "GBP": ["£"],
        "EUR": ["€"],
        "MYR": ["RM"],
    }
    for currency, symbols in safe_symbols.items():
        for symbol in symbols:
            if symbol in text:
                return currency

    return "SGD"

def convert_to_sgd(amount: float, from_currency: str) -> float:
    """Convert amount to SGD using frankfurter.app (free, no key needed)."""
    if from_currency == "SGD":
        return round(amount, 2)
    try:
        response = requests.get(
            f"https://api.frankfurter.app/latest?from={from_currency}&to=SGD",
            timeout=5
        )
        data = response.json()
        rate = data["rates"]["SGD"]
        return round(amount * rate, 2)
    except Exception as e:
        logger.error(f"Currency conversion failed: {e}")
        return round(amount, 2)  # Return original if conversion fails


# ── Field extractors ───────────────────────────────────────────────────────────

def extract_merchant(lines: list[str]) -> str:
    """
    Extract merchant name from receipt.
    Takes the longest all-caps line in the first 5 lines,
    which is typically the most complete version of the merchant name.
    """
    candidates = []
    for line in lines[:5]:
        line = line.strip().rstrip(":")
        if not line or re.match(r"^[\d\s\-\+\*]+$", line):
            continue
        if re.match(r"^[A-Z][A-Z\s]+$", line) and len(line) <= 30:
            candidates.append(line)
    if candidates:
        return max(candidates, key=len)
    return lines[0].strip().rstrip(":") if lines else "Unknown"

def extract_location(lines: list[str]) -> str:
    """Look for address-like lines near the top of the receipt."""
    location_parts = []
    address_pattern = re.compile(
        r'(mall|plaza|centre|center|airport|road|rd|street|st|ave|blvd|#\d|singapore|s\(\d{6}\)|\d{6})',
        re.IGNORECASE
    )
    for line in lines[1:10]:
        line = line.strip()
        if line and address_pattern.search(line):
            location_parts.append(line)
        if len(location_parts) == 2:
            break
    return ", ".join(location_parts) if location_parts else "Unknown"

def extract_date(text: str):
    """
    Extract date and time from receipt text.
    Returns ISO 8601 string for Supabase timestamptz, or None if not found.
    """
    from datetime import datetime as dt

    formats = [
        (r'\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}', "%d/%m/%Y %H:%M"),
        (r'\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}', "%d-%m-%Y %H:%M"),
        (r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', "%Y-%m-%d %H:%M"),
        (r'\d{2}/\d{2}/\d{4}',               "%d/%m/%Y"),
        (r'\d{2}-\d{2}-\d{4}',               "%d-%m-%Y"),
    ]
    for pattern, fmt in formats:
        match = re.search(pattern, text)
        if match:
            try:
                parsed = dt.strptime(match.group().strip(), fmt)
                return parsed.isoformat()  # e.g. 2026-05-19T18:59:00
            except ValueError:
                continue
    return None

def extract_total(text: str) -> float:
    """Extract total amount from receipt."""
    patterns = [
        r'total\s*\$?\s*([\d,]+\.\d{2})',
        r'amount\s*due\s*\$?\s*([\d,]+\.\d{2})',
        r'grand\s*total\s*\$?\s*([\d,]+\.\d{2})',
        r'total\s*amount\s*\$?\s*([\d,]+\.\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
    return 0.0

def extract_payment_method(text: str) -> str:
    """Detect payment method from receipt text."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["paynow", "pay now"]):
        return "PayNow"
    if any(k in text_lower for k in ["paywave", "pay wave", "contactless"]):
        return "Contactless Card"
    if any(k in text_lower for k in ["visa", "mastercard", "amex", "credit card"]):
        return "Credit Card"
    if "nets" in text_lower:
        return "NETS"
    if "cash" in text_lower:
        return "Cash"
    if "grabpay" in text_lower:
        return "GrabPay"
    if "paylah" in text_lower:
        return "PayLah"
    return "Unknown"

def extract_items(lines: list[str]) -> list[dict]:
    """
    Extract line items from receipt.
    Handles two patterns:
      1. Barcode → Item name → Price (Don Don Donki style)
      2. Item name followed by price on same or next line
    """
    items = []
    barcode_pattern = re.compile(r'^\d{8,}$')
    price_pattern = re.compile(r'^\$?([\d,]+\.\d{2})$')
    
    i = 0
    pending_name = None

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # Pattern 1: barcode line → skip, next line is item name
        if barcode_pattern.match(line):
            if i + 1 < len(lines):
                pending_name = lines[i + 1].strip()
                i += 2
                continue

        # Price line
        price_match = price_pattern.match(line)
        if price_match and pending_name:
            items.append({
                "name": pending_name,
                "price": float(price_match.group(1).replace(",", ""))
            })
            pending_name = None
            i += 1
            continue

        # Pattern 2: "Item name    9.90" on same line
        inline_match = re.match(r'^(.+?)\s{2,}\$?([\d,]+\.\d{2})$', line)
        if inline_match:
            name = inline_match.group(1).strip()
            price = float(inline_match.group(2).replace(",", ""))
            # Skip summary lines
            if not any(k in name.lower() for k in ["total", "gst", "cash", "change", "credit", "nets", "visa", "mastercard"]):
                items.append({"name": name, "price": price})
            i += 1
            continue

        # If no price follows a pending name after 2 lines, reset
        if pending_name:
            pending_name = line
        
        i += 1

    # Extract GST separately
    gst_match = re.search(r'gst\s*amount\s*([\d,]+\.\d{2})', "\n".join(lines), re.IGNORECASE)
    if gst_match:
        items.append({
            "name": "GST",
            "price": float(gst_match.group(1).replace(",", ""))
        })

    return items


# ── Main parse function ────────────────────────────────────────────────────────

def parse_receipt(ocr_text: str) -> dict:
    """
    Parse OCR text into structured receipt data.
    Returns a dict with all extracted fields.
    """
    lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]

    currency = detect_currency(ocr_text)
    total_raw = extract_total(ocr_text)
    total_sgd = convert_to_sgd(total_raw, currency)
    items = extract_items(lines)

    # Convert item prices if needed
    if currency != "SGD" and total_raw > 0:
        rate = total_sgd / total_raw if total_raw else 1
        for item in items:
            item["price_sgd"] = round(item["price"] * rate, 2)

    return {
        "merchant": extract_merchant(lines),
        "location": extract_location(lines),
        "receipt_date": extract_date(ocr_text),
        "total_amount": total_sgd,
        "original_currency": currency,
        "payment_method": extract_payment_method(ocr_text),
        "items": items,
    }


def format_for_telegram(parsed: dict) -> str:
    """Format parsed receipt data into a readable Telegram message."""
    from datetime import datetime as dt

    date_str = parsed.get("receipt_date")
    if date_str:
        try:
            date_str = dt.fromisoformat(date_str).strftime("%d %b %Y %H:%M")
        except ValueError:
            pass
    else:
        date_str = "Unknown"

    lines = [
        f"🏪 *Merchant:* {parsed['merchant']}",
        f"📍 *Location:* {parsed['location']}",
        f"📅 *Date:* {date_str}",
        f"💳 *Payment:* {parsed['payment_method']}",
    ]

    if parsed['items']:
        lines.append("\n🧾 *Items:*")
        for item in parsed['items']:
            price = item.get('price_sgd', item['price'])
            name = item['name']
            if name.upper() == "GST":
                name = f"GST (not separately charged)"
            lines.append(f"  • {name}    S${price:.2f}")

    lines.append("")
    if parsed['original_currency'] != 'SGD':
        lines.append(f"💰 *Total (SGD):* S${parsed['total_amount']:.2f} _{parsed['original_currency']} converted_")
    else:
        lines.append(f"💰 *Total (GST incl.):* S${parsed['total_amount']:.2f}")

    return "\n".join(lines)