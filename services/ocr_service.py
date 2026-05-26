import easyocr
import logging

logger = logging.getLogger(__name__)

# Initialise once at import time — this loads the model (~1GB, takes a few seconds on first run)
# English only for now; add more languages like ['en', 'ch_sim'] if needed
reader = easyocr.Reader(['en'], gpu=False)


def extract_text(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes.
    Returns extracted text as a single string, one line per detected block.
    """
    try:
        results = reader.readtext(image_bytes, detail=0, paragraph=True)
        if not results:
            return "No text detected."
        return "\n".join(results)
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return "OCR failed — could not read text from image."