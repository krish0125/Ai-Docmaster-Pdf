"""Utility Services — Phase 8.

QR code, Barcode, PDF metadata viewer/editor, Word count, Password generator,
Web-to-PDF (URL → PDF), color picker, Base64 encode/decode.
"""

from __future__ import annotations
import os
import uuid
import json


def _out(upload_folder: str, suffix: str) -> tuple[str, str]:
    fname = f"util_{uuid.uuid4().hex}{suffix}"
    path  = os.path.join(upload_folder, fname)
    os.makedirs(upload_folder, exist_ok=True)
    return fname, path


# ───────────────────────────────────────────────────────────────────────────
# QR Code
# ───────────────────────────────────────────────────────────────────────────

def generate_qr(data: str, size: int, upload_folder: str) -> tuple[str, str]:
    """Generate a QR code PNG for *data*."""
    try:
        import qrcode
    except ImportError:
        raise RuntimeError("qrcode not installed. Run: pip install qrcode[pil]")

    qr = qrcode.QRCode(box_size=max(1, size // 37), border=2,
                       error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    fname, fpath = _out(upload_folder, '.png')
    img.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Barcode
# ───────────────────────────────────────────────────────────────────────────

def generate_barcode(data: str, barcode_type: str, upload_folder: str) -> tuple[str, str]:
    """Generate a barcode image (code128, ean13, ean8, upc-a)."""
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError:
        raise RuntimeError("python-barcode not installed. Run: pip install python-barcode Pillow")

    fname_base = f"util_{uuid.uuid4().hex}"
    out_path   = os.path.join(upload_folder, fname_base)
    os.makedirs(upload_folder, exist_ok=True)

    bc_type = barcode_type.lower().replace('-', '')
    cls     = barcode.get_barcode_class(bc_type)
    bc      = cls(data, writer=ImageWriter())
    saved   = bc.save(out_path)     # saves as <fname_base>.png
    fname   = os.path.basename(saved)
    return fname, saved


# ───────────────────────────────────────────────────────────────────────────
# PDF Metadata
# ───────────────────────────────────────────────────────────────────────────

def get_pdf_metadata(pdf_path: str) -> dict:
    """Extract metadata from a PDF."""
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    info   = reader.metadata or {}
    return {
        'page_count':  len(reader.pages),
        'title':       str(info.get('/Title', '')),
        'author':      str(info.get('/Author', '')),
        'subject':     str(info.get('/Subject', '')),
        'creator':     str(info.get('/Creator', '')),
        'producer':    str(info.get('/Producer', '')),
        'created':     str(info.get('/CreationDate', '')),
        'modified':    str(info.get('/ModDate', '')),
        'keywords':    str(info.get('/Keywords', '')),
        'encrypted':   reader.is_encrypted,
    }


def set_pdf_metadata(pdf_path: str, title: str, author: str,
                     subject: str, keywords: str,
                     upload_folder: str) -> tuple[str, str]:
    """Write metadata fields into a PDF."""
    try:
        import pikepdf
    except ImportError:
        raise RuntimeError("pikepdf not installed. Run: pip install pikepdf")

    fname, fpath = _out(upload_folder, '.pdf')
    with pikepdf.open(pdf_path) as pdf:
        with pdf.open_metadata() as meta:
            if title:    meta['dc:title']   = title
            if author:   meta['dc:creator'] = [author]
            if subject:  meta['dc:subject'] = [subject]
            if keywords: meta['pdf:Keywords'] = keywords
        pdf.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Word / Character Count
# ───────────────────────────────────────────────────────────────────────────

def count_words(text: str) -> dict:
    """Return word, character, sentence, and paragraph counts."""
    import re
    words      = text.split()
    chars_no_sp = text.replace(' ', '').replace('\n', '')
    sentences  = re.split(r'[.!?]+', text)
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    return {
        'words':           len(words),
        'characters':      len(text),
        'chars_no_spaces': len(chars_no_sp),
        'sentences':       len([s for s in sentences if s.strip()]),
        'paragraphs':      len(paragraphs),
        'avg_word_length': round(sum(len(w) for w in words) / len(words), 1) if words else 0,
        'reading_time_min': round(len(words) / 200, 1),  # avg 200 wpm
    }


# ───────────────────────────────────────────────────────────────────────────
# Password Generator
# ───────────────────────────────────────────────────────────────────────────

def generate_password(length: int, use_upper: bool, use_lower: bool,
                      use_digits: bool, use_special: bool) -> dict:
    """Generate a cryptographically random password."""
    import secrets
    import string

    pool = ''
    if use_upper:   pool += string.ascii_uppercase
    if use_lower:   pool += string.ascii_lowercase
    if use_digits:  pool += string.digits
    if use_special: pool += '!@#$%^&*()-_=+[]{}|;:,.<>?'

    if not pool:
        pool = string.ascii_letters + string.digits

    password = ''.join(secrets.choice(pool) for _ in range(length))

    # Strength score
    score = sum([use_upper, use_lower, use_digits, use_special])
    if length >= 16 and score >= 3:
        strength = 'Strong'
    elif length >= 12 and score >= 2:
        strength = 'Medium'
    else:
        strength = 'Weak'

    return {'password': password, 'length': length, 'strength': strength}


# ───────────────────────────────────────────────────────────────────────────
# Web to PDF
# ───────────────────────────────────────────────────────────────────────────

def web_to_pdf(url: str, upload_folder: str) -> tuple[str, str]:
    """Convert a URL to PDF via weasyprint or pdfkit+wkhtmltopdf."""
    fname, fpath = _out(upload_folder, '.pdf')

    # Attempt 1: weasyprint
    try:
        from weasyprint import HTML
        HTML(url=url).write_pdf(fpath)
        if os.path.isfile(fpath):
            return fname, fpath
    except ImportError:
        pass
    except Exception as e:
        print(f"[UtilService] weasyprint failed: {e}")

    # Attempt 2: pdfkit
    try:
        import pdfkit
        pdfkit.from_url(url, fpath)
        if os.path.isfile(fpath):
            return fname, fpath
    except ImportError:
        pass
    except Exception as e:
        print(f"[UtilService] pdfkit failed: {e}")

    raise RuntimeError(
        "web-to-PDF failed. Install weasyprint (`pip install weasyprint`) or "
        "pdfkit + wkhtmltopdf (`pip install pdfkit` + https://wkhtmltopdf.org)."
    )


# ───────────────────────────────────────────────────────────────────────────
# Base64 Encode / Decode
# ───────────────────────────────────────────────────────────────────────────

def base64_encode(text: str) -> str:
    import base64 as b64
    return b64.b64encode(text.encode('utf-8')).decode('utf-8')


def base64_decode(encoded: str) -> str:
    import base64 as b64
    return b64.b64decode(encoded.encode('utf-8')).decode('utf-8')


# ───────────────────────────────────────────────────────────────────────────
# Color Picker Info
# ───────────────────────────────────────────────────────────────────────────

def get_color_info(hex_color: str) -> dict:
    """Convert a hex color to RGB, HSL, and CMYK."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r_n, g_n, b_n = r / 255, g / 255, b / 255
    cmax = max(r_n, g_n, b_n)
    cmin = min(r_n, g_n, b_n)
    delta = cmax - cmin

    # Hue
    if delta == 0:    h = 0
    elif cmax == r_n: h = 60 * (((g_n - b_n) / delta) % 6)
    elif cmax == g_n: h = 60 * (((b_n - r_n) / delta) + 2)
    else:             h = 60 * (((r_n - g_n) / delta) + 4)

    # Lightness
    l = (cmax + cmin) / 2
    s = 0 if delta == 0 else delta / (1 - abs(2 * l - 1))

    # CMYK
    if cmax == 0:
        c_ = m_ = y_ = 0; k_ = 1
    else:
        k_ = 1 - cmax
        c_ = (1 - r_n - k_) / (1 - k_)
        m_ = (1 - g_n - k_) / (1 - k_)
        y_ = (1 - b_n - k_) / (1 - k_)

    return {
        'hex': f'#{hex_color.upper()}',
        'rgb': {'r': r, 'g': g, 'b': b},
        'hsl': {'h': round(h, 1), 's': round(s * 100, 1), 'l': round(l * 100, 1)},
        'cmyk': {'c': round(c_ * 100, 1), 'm': round(m_ * 100, 1),
                 'y': round(y_ * 100, 1), 'k': round(k_ * 100, 1)},
    }
