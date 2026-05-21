"""OCR engine — extract text from images using OpenCV pre-processing + Tesseract.

Handles gracefully when Tesseract is not installed.
"""

import os

import numpy as np
from PIL import Image

from config import Config

# ---------------------------------------------------------------------------
# Tesseract availability check
# ---------------------------------------------------------------------------
_TESSERACT_AVAILABLE = False

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_PATH
    # Quick check: does the binary actually exist?
    if os.path.isfile(Config.TESSERACT_PATH):
        _TESSERACT_AVAILABLE = True
    else:
        print(f"[OCR] Tesseract binary not found at {Config.TESSERACT_PATH}")
except ImportError:
    print("[OCR] pytesseract is not installed")
    pytesseract = None  # type: ignore[assignment]

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    print("[OCR] opencv-python (cv2) is not installed")
    cv2 = None  # type: ignore[assignment]
    _CV2_AVAILABLE = False


# ---------------------------------------------------------------------------
# Image pre-processing
# ---------------------------------------------------------------------------

def preprocess_image(image: np.ndarray) -> np.ndarray:
    """Convert to grayscale → Gaussian blur → Otsu threshold.

    Improves OCR accuracy on noisy / low-contrast images.
    """
    if image is None:
        raise ValueError("Empty image passed to preprocess_image")

    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Otsu's thresholding
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresh


# ---------------------------------------------------------------------------
# Core OCR
# ---------------------------------------------------------------------------

def extract_text_from_image(image_path: str) -> dict:
    """Run OCR on a single image file.

    Returns ``{text, confidence, word_count}`` or an error dict.
    """
    if not _TESSERACT_AVAILABLE:
        return {
            'text': '',
            'confidence': 0,
            'word_count': 0,
            'error': (
                'Tesseract OCR is not installed or not found at '
                f'"{Config.TESSERACT_PATH}". Please install Tesseract and '
                'set TESSERACT_PATH in your .env file.'
            ),
        }

    if not os.path.isfile(image_path):
        return {'text': '', 'confidence': 0, 'word_count': 0, 'error': 'Image file not found'}

    try:
        if _CV2_AVAILABLE:
            # Use OpenCV for pre-processing
            image = cv2.imread(image_path)
            if image is None:
                return {'text': '', 'confidence': 0, 'word_count': 0, 'error': 'Could not read image'}

            processed = preprocess_image(image)

            # OCR with confidence data
            data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            text = pytesseract.image_to_string(processed).strip()
        else:
            # Fallback: use PIL directly
            pil_image = Image.open(image_path)
            text = pytesseract.image_to_string(pil_image).strip()

            data = pytesseract.image_to_data(pil_image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        word_count = len(text.split()) if text else 0

        return {
            'text': text,
            'confidence': round(avg_confidence, 2),
            'word_count': word_count,
        }
    except Exception as e:
        return {'text': '', 'confidence': 0, 'word_count': 0, 'error': str(e)}


# ---------------------------------------------------------------------------
# Scanned PDF OCR
# ---------------------------------------------------------------------------

def extract_text_from_pdf_image(pdf_path: str) -> str:
    """Extract text from a scanned / image-based PDF.

    Strategy:
      1. Try pdfplumber first (fast, works for digital PDFs).
      2. If no text is found, convert each page to an image and OCR.
    """
    # --- Attempt text-layer extraction first ---
    try:
        import pdfplumber
        texts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    texts.append(t)
        if texts:
            return '\n\n'.join(texts)
    except Exception:
        pass  # fall through to OCR

    # --- OCR fallback ---
    if not _TESSERACT_AVAILABLE:
        return '[OCR unavailable] Tesseract is not installed.'

    try:
        from pypdf import PdfReader
        from PIL import Image as PILImage
        import io

        reader = PdfReader(pdf_path)
        ocr_texts: list[str] = []

        for page_num, page in enumerate(reader.pages):
            # Try to extract images embedded in the page
            images_extracted = False
            for image_key in page.images:
                try:
                    img_data = image_key.data
                    pil_img = PILImage.open(io.BytesIO(img_data))
                    # Convert to RGB if needed (e.g. CMYK)
                    if pil_img.mode not in ('RGB', 'L'):
                        pil_img = pil_img.convert('RGB')
                    img_array = np.array(pil_img)

                    if _CV2_AVAILABLE:
                        processed = preprocess_image(img_array)
                        text = pytesseract.image_to_string(processed)
                    else:
                        text = pytesseract.image_to_string(pil_img)

                    if text.strip():
                        ocr_texts.append(text.strip())
                        images_extracted = True
                except Exception:
                    continue

            if not images_extracted:
                # If no images could be extracted, note it
                ocr_texts.append(f'[Page {page_num + 1}: no extractable content]')

        return '\n\n'.join(ocr_texts) if ocr_texts else 'No text could be extracted from this PDF.'
    except Exception as e:
        return f'OCR extraction failed: {str(e)}'
