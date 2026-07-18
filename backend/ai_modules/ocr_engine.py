"""Phase 5 OCR Engine — handles Tesseract for standard PDFs/Images and Gemini Vision for handwriting."""

import os
import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
from config import Config

pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_PATH

def extract_text_from_image(image_path: str, lang: str = 'eng') -> str:
    """Standard OCR using Tesseract for printed text."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Denoise and threshold
    gray = cv2.medianBlur(gray, 3)
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(gray, lang=lang, config=custom_config)
    return text.strip()

def extract_text_from_pdf_image(pdf_path: str, lang: str = 'eng') -> str:
    """Standard OCR for scanned PDFs by converting pages to images and using Tesseract."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
    poppler_path = getattr(Config, 'POPPLER_PATH', None)
    pages = convert_from_path(pdf_path, 300, poppler_path=poppler_path)
    full_text = []
    
    for page in pages:
        img = np.array(page)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(gray, lang=lang, config=custom_config)
        full_text.append(text)
        
    return "\n\n".join(full_text).strip()

def handwriting_ocr(image_path: str) -> dict:
    """Recognise handwritten text using Gemini Vision multimodal (no Tesseract needed)."""
    import base64
    from ai_modules.chat_engine import get_client
    from ai_modules.exceptions import GeminiAPIError, call_gemini_with_retry

    client = get_client()
    if not client:
        raise GeminiAPIError("Gemini API client not initialized. Check GEMINI_API_KEY.", "invalid_key", 401)

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Detect MIME type from extension
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                '.gif': 'image/gif', '.bmp': 'image/bmp', '.webp': 'image/webp',
                '.tiff': 'image/tiff', '.tif': 'image/tiff'}
    mime_type = mime_map.get(ext, 'image/jpeg')

    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()

    prompt = (
        "Transcribe the handwritten text in this image perfectly. "
        "Maintain original formatting. Return ONLY the transcribed text, "
        "without markdown blocks or conversational fillers."
    )

    # google-genai SDK multimodal: inline_data with bytes
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_bytes,
                    }
                },
                {"text": prompt},
            ],
        }
    ]

    response = call_gemini_with_retry(
        client=client,
        model="gemini-2.5-flash",
        contents=contents,
    )

    text = (response.text or "").strip()
    return {"text": text, "method": "gemini_vision"}

# ---------------------------------------------------------------------------
# Phase 5 — Extraction utilities
# ---------------------------------------------------------------------------

def extract_tables_from_pdf(pdf_path: str) -> list:
    import pdfplumber
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            for tbl in page_tables:
                tables.append({"page": i + 1, "data": tbl})
    return tables

def extract_images_from_pdf(pdf_path: str, output_dir: str) -> list:
    import fitz # PyMuPDF
    import os
    import uuid
    doc = fitz.open(pdf_path)
    images = []
    for i, page in enumerate(doc):
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            filename = f"extracted_{uuid.uuid4().hex[:8]}.{image_ext}"
            file_path = os.path.join(output_dir, filename)
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            images.append({"page": i + 1, "filename": filename})
    return images

def multilang_ocr(file_path: str, lang: str = 'hin+eng') -> dict:
    import os
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        text = extract_text_from_pdf_image(file_path, lang=lang)
    else:
        text = extract_text_from_image(file_path, lang=lang)
    return {"text": text, "lang_used": lang, "word_count": len(text.split())}
