import os
import json
import logging
from google.cloud import vision
from google.oauth2 import service_account

logger = logging.getLogger(__name__)


def _make_client():
    """
    Create Vision client from env var JSON (Render) or local credentials file (local dev).
    """
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        # Running on Render — credentials stored as env var
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return vision.ImageAnnotatorClient(credentials=credentials)
    else:
        # Running locally — credentials file path set in .env
        return vision.ImageAnnotatorClient()


client = _make_client()


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

        return texts[0].description.strip()

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return "OCR failed — could not read text from image."