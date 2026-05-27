import logging
from google.cloud import vision

logger = logging.getLogger(__name__)

# Initialise once at import time
client = vision.ImageAnnotatorClient()


def extract_text(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes using Google Cloud Vision.
    Returns extracted text as a single string.
    """
    try:
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)

        if response.error.message:
            logger.error(f"Google Vision error: {response.error.message}")
            return "OCR failed — Google Vision returned an error."

        texts = response.text_annotations
        if not texts:
            return "No text detected."

        # texts[0].description contains the full extracted text
        return texts[0].description.strip()

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return "OCR failed — could not read text from image."