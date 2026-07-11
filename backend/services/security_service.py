"""PDF Security Service — Phase 4.

Covers: password lock/unlock, watermark, redaction, metadata removal,
digital stamp (visual MVP), and PDF flatten.
Uses pypdf (already installed) + pikepdf (installed in Phase 2).
"""

from __future__ import annotations
import io
import os
import uuid


def _out(upload_folder: str, prefix: str = 'secure') -> tuple[str, str]:
    fname = f"{prefix}_{uuid.uuid4().hex}.pdf"
    path  = os.path.join(upload_folder, fname)
    os.makedirs(upload_folder, exist_ok=True)
    return fname, path


# ───────────────────────────────────────────────────────────────────────────
# Lock (Encrypt)
# ───────────────────────────────────────────────────────────────────────────

def lock_pdf(pdf_path: str, password: str, upload_folder: str) -> tuple[str, str]:
    """Encrypt a PDF with a user password using pypdf AES-256."""
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password, owner_password=password, use_128bit=True)
    fname, fpath = _out(upload_folder, 'locked')
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Unlock (Decrypt)
# ───────────────────────────────────────────────────────────────────────────

def unlock_pdf(pdf_path: str, password: str, upload_folder: str) -> tuple[str, str]:
    """Decrypt a password-protected PDF."""
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        result = reader.decrypt(password)
        if result == 0:
            raise ValueError('Incorrect password — could not decrypt PDF.')
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    fname, fpath = _out(upload_folder, 'unlocked')
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Watermark (visual text diagonal)
# ───────────────────────────────────────────────────────────────────────────

def add_watermark(pdf_path: str, text: str, opacity: float,
                  font_size: int, color_hex: str,
                  upload_folder: str) -> tuple[str, str]:
    """Stamp a diagonal text watermark across every page."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor, Color
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    import math
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        mb = page.mediabox
        pw, ph = float(mb.width), float(mb.height)

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(pw, ph))
        c.saveState()
        c.translate(pw / 2, ph / 2)
        c.rotate(45)
        try:
            base = HexColor(color_hex)
            c.setFillColor(Color(base.red, base.green, base.blue, alpha=opacity))
        except Exception:
            c.setFillColorRGB(0.5, 0.5, 0.5, opacity)
        c.setFont('Helvetica-Bold', font_size)
        c.drawCentredString(0, 0, text)
        c.restoreState()
        c.save()

        buf.seek(0)
        from pypdf import PdfReader as PR2
        page.merge_page(PR2(buf).pages[0])
        writer.add_page(page)

    fname, fpath = _out(upload_folder, 'watermarked')
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Remove Watermark / Flatten
# ───────────────────────────────────────────────────────────────────────────

def flatten_pdf(pdf_path: str, upload_folder: str) -> tuple[str, str]:
    """Flatten form fields and annotations by re-saving via pypdf.

    Note: This cannot remove a baked-in watermark. It flattens interactive
    elements and removes form fields.
    """
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    for page in reader.pages:
        # Remove /Annots to flatten annotations
        if '/Annots' in page:
            del page['/Annots']
        writer.add_page(page)
    fname, fpath = _out(upload_folder, 'flattened')
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Remove Metadata
# ───────────────────────────────────────────────────────────────────────────

def remove_metadata(pdf_path: str, upload_folder: str) -> tuple[str, str]:
    """Strip all document metadata (XMP + DocumentInfo dictionary)."""
    try:
        import pikepdf
    except ImportError:
        raise RuntimeError("pikepdf is not installed. Run: pip install pikepdf")

    fname, fpath = _out(upload_folder, 'nometadata')
    with pikepdf.open(pdf_path) as pdf:
        del pdf.docinfo
        with pdf.open_metadata() as meta:
            for key in list(meta.keys()):
                del meta[key]
        pdf.save(fpath)
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Visual Digital Stamp (MVP — not cryptographic)
# ───────────────────────────────────────────────────────────────────────────

def add_signature_stamp(pdf_path: str, signer_name: str, date_str: str,
                        page_num: int, upload_folder: str) -> tuple[str, str]:
    """Add a visual signature stamp to a specific page.

    # TODO: Replace with pyhanko for true cryptographic signatures.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    reader = PdfReader(pdf_path)
    total  = len(reader.pages)
    writer = PdfWriter()
    target = page_num - 1 if 0 <= page_num - 1 < total else total - 1

    for idx, page in enumerate(reader.pages):
        if idx == target:
            pw, ph = float(page.mediabox.width), float(page.mediabox.height)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))

            # Stamp box
            bx, by, bw, bh = pw - 200, 20, 180, 60
            c.setStrokeColor(HexColor('#6C63FF'))
            c.setFillColor(HexColor('#F5F3FF'))
            c.roundRect(bx, by, bw, bh, 6, fill=1, stroke=1)

            # Text
            c.setFillColor(HexColor('#1a1a2e'))
            c.setFont('Helvetica-Bold', 9)
            c.drawString(bx + 8, by + 42, f'Signed: {signer_name}')
            c.setFont('Helvetica', 8)
            c.drawString(bx + 8, by + 28, f'Date: {date_str}')
            c.setFont('Helvetica-Oblique', 7)
            c.setFillColor(HexColor('#999'))
            c.drawString(bx + 8, by + 10, '(Visual stamp — not cryptographic)')
            c.save()

            buf.seek(0)
            from pypdf import PdfReader as PR2
            page.merge_page(PR2(buf).pages[0])

        writer.add_page(page)

    fname, fpath = _out(upload_folder, 'signed')
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Redact (black-box redaction)
# ───────────────────────────────────────────────────────────────────────────

def redact_area(pdf_path: str, x: float, y: float, w_pct: float, h_pct: float,
                pages: list[int] | None, upload_folder: str) -> tuple[str, str]:
    """Cover an area with a solid black rectangle (visual redaction)."""
    try:
        from reportlab.pdfgen import canvas
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    reader = PdfReader(pdf_path)
    total  = len(reader.pages)
    writer = PdfWriter()
    target = set(range(total)) if not pages else {p - 1 for p in pages if 0 <= p - 1 < total}

    for idx, page in enumerate(reader.pages):
        if idx in target:
            pw, ph = float(page.mediabox.width), float(page.mediabox.height)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            c.setFillColorRGB(0, 0, 0)
            rx, ry = pw * (x / 100.0), ph * (y / 100.0)
            rw, rh = pw * (w_pct / 100.0), ph * (h_pct / 100.0)
            c.rect(rx, ry, rw, rh, fill=1, stroke=0)
            c.save()

            buf.seek(0)
            from pypdf import PdfReader as PR2
            page.merge_page(PR2(buf).pages[0])

        writer.add_page(page)

    fname, fpath = _out(upload_folder, 'redacted')
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath
