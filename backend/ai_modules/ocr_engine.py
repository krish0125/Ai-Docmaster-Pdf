"""Phase 5 OCR Engine — handles Tesseract for standard PDFs/Images and Grok Vision for handwriting."""

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
        
    pages = convert_from_path(pdf_path, 300)
    full_text = []
    
    for page in pages:
        img = np.array(page)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(gray, lang=lang, config=custom_config)
        full_text.append(text)
        
    return "\n\n".join(full_text).strip()

def handwriting_ocr(image_path: str) -> dict:
    """Recognise handwritten text using Grok vision (no Tesseract needed)."""
    import base64
    from ai_modules.chat_engine import get_client
    from ai_modules.exceptions import GrokAPIError, call_grok_with_retry
    
    client = get_client()
    if not client:
        raise GrokAPIError("Grok API client not initialized. Check GROK_API_KEY.", "invalid_key", 401)
        
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
    prompt = "Transcribe the handwritten text in this image perfectly. Maintain original formatting. Return ONLY the transcribed text, without markdown blocks or conversational fillers."
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ]
    
    response = call_grok_with_retry(
        client=client,
        model="grok-2-vision-1212",
        messages=messages,
        max_tokens=2048
    )
    
    text = response.choices[0].message.content.strip()
    return {"text": text, "method": "grok_vision"}
