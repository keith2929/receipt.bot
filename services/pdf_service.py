import logging
from pdf2image import convert_from_bytes
import io

logger = logging.getLogger(__name__)


def pdf_to_image_bytes(pdf_bytes: bytes) -> bytes:
    """
    Convert first page of a PDF to JPEG bytes for OCR.
    """
    try:
        images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
        if not images:
            return b""
        img_byte_arr = io.BytesIO()
        images[0].save(img_byte_arr, format="JPEG")
        return img_byte_arr.getvalue()
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        return b""