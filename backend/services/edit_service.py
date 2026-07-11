"""PDF Editing Service — Phase 3.

Adds text overlays, image stamps, watermarks, highlights (annotation),
header/footer, page numbers, and form-field text via reportlab + pypdf.

Strategy: Build an overlay PDF with reportlab and merge it onto the source
using PdfWriter.merge_page(). This preserves the original content.
"""

from __future__ import annotations
import io
import os
import uuid


def _overlay_path(upload_folder: str, suffix: str = '.pdf') -> tuple[str, str]:
    fname = f"edited_{uuid.uuid4().hex}{suffix}"
    path  = os.path.join(upload_folder, fname)
    os.makedirs(upload_folder, exist_ok=True)
    return fname, path


def _page_size_pts(page) -> tuple[float, float]:
    """Return (width, height) in points from a pypdf page."""
    mb = page.mediabox
    return float(mb.width), float(mb.height)


# ───────────────────────────────────────────────────────────────────────────
# Add Text Overlay
# ───────────────────────────────────────────────────────────────────────────

def add_text(pdf_path: str, text: str, x: float, y: float,
             font_size: int, color_hex: str, pages: list[int] | None,
             upload_folder: str) -> tuple[str, str]:
    """Overlay *text* at position (*x*, *y*) (% of page size) on target pages."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    reader = PdfReader(pdf_path)
    total  = len(reader.pages)
    writer = PdfWriter()

    target = set(range(total)) if not pages else {p - 1 for p in pages if 0 <= p - 1 < total}

    for idx, page in enumerate(reader.pages):
        if idx in target:
            w, h = _page_size_pts(page)
            px, py = w * (x / 100.0), h * (y / 100.0)

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            try:
                c.setFillColor(HexColor(color_hex))
            except Exception:
                c.setFillColorRGB(0, 0, 0)
            c.setFont('Helvetica', font_size)
            c.drawString(px, py, text)
            c.save()

            buf.seek(0)
            from pypdf import PdfReader as PR2
            overlay = PR2(buf)
            page.merge_page(overlay.pages[0])

        writer.add_page(page)

    fname, fpath = _overlay_path(upload_folder)
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Add Image Stamp
# ───────────────────────────────────────────────────────────────────────────

def add_image(pdf_path: str, image_path: str, x: float, y: float,
              width_pct: float, pages: list[int] | None,
              upload_folder: str) -> tuple[str, str]:
    """Stamp an image on the PDF at percentage-based position/size."""
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
            w, h = _page_size_pts(page)
            px   = w * (x / 100.0)
            py   = h * (y / 100.0)
            pw   = w * (width_pct / 100.0)

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(w, h))
            c.drawImage(image_path, px, py, width=pw, preserveAspectRatio=True, mask='auto')
            c.save()

            buf.seek(0)
            from pypdf import PdfReader as PR2
            overlay = PR2(buf)
            page.merge_page(overlay.pages[0])

        writer.add_page(page)

    fname, fpath = _overlay_path(upload_folder)
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Highlight / Annotate (visual coloured rectangle — annotation box)
# ───────────────────────────────────────────────────────────────────────────

def highlight_area(pdf_path: str, x: float, y: float,
                   w_pct: float, h_pct: float,
                   color_hex: str, opacity: float,
                   pages: list[int] | None, upload_folder: str) -> tuple[str, str]:
    """Draw a semi-transparent coloured rectangle on the specified pages."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import HexColor, Color
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    reader = PdfReader(pdf_path)
    total  = len(reader.pages)
    writer = PdfWriter()

    target = set(range(total)) if not pages else {p - 1 for p in pages if 0 <= p - 1 < total}

    for idx, page in enumerate(reader.pages):
        if idx in target:
            pw, ph = _page_size_pts(page)
            rx, ry = pw * (x / 100.0), ph * (y / 100.0)
            rw, rh = pw * (w_pct / 100.0), ph * (h_pct / 100.0)

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            try:
                base = HexColor(color_hex)
                c.setFillColor(Color(base.red, base.green, base.blue, alpha=opacity))
            except Exception:
                c.setFillColorRGB(1, 1, 0, opacity)
            c.setStrokeAlpha(0)
            c.rect(rx, ry, rw, rh, fill=1, stroke=0)
            c.save()

            buf.seek(0)
            from pypdf import PdfReader as PR2
            page.merge_page(PR2(buf).pages[0])

        writer.add_page(page)

    fname, fpath = _overlay_path(upload_folder)
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Header & Footer
# ───────────────────────────────────────────────────────────────────────────

def add_header_footer(pdf_path: str, header: str, footer: str,
                      font_size: int, upload_folder: str) -> tuple[str, str]:
    """Add header and footer text to every page."""
    try:
        from reportlab.pdfgen import canvas
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        pw, ph = _page_size_pts(page)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(pw, ph))
        c.setFont('Helvetica', font_size)
        c.setFillColorRGB(0.3, 0.3, 0.3)

        if header:
            c.drawCentredString(pw / 2, ph - font_size * 1.5, header)
        if footer:
            c.drawCentredString(pw / 2, font_size * 0.5, footer)
        c.save()

        buf.seek(0)
        from pypdf import PdfReader as PR2
        page.merge_page(PR2(buf).pages[0])
        writer.add_page(page)

    fname, fpath = _overlay_path(upload_folder)
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# Page Numbers
# ───────────────────────────────────────────────────────────────────────────

def add_page_numbers(pdf_path: str, position: str, font_size: int,
                     start: int, upload_folder: str) -> tuple[str, str]:
    """Stamp page numbers on every page.

    *position*: 'bottom-center' | 'bottom-right' | 'top-center' | 'top-right'
    """
    try:
        from reportlab.pdfgen import canvas
        from pypdf import PdfReader, PdfWriter
    except ImportError as e:
        raise RuntimeError(f"Missing dependency: {e}")

    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for num, page in enumerate(reader.pages, start=start):
        pw, ph = _page_size_pts(page)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(pw, ph))
        c.setFont('Helvetica', font_size)
        c.setFillColorRGB(0.4, 0.4, 0.4)
        label = str(num)

        pos = position.lower()
        if 'top' in pos:
            vy = ph - font_size * 1.5
        else:
            vy = font_size * 0.5

        if 'right' in pos:
            c.drawRightString(pw - 20, vy, label)
        else:
            c.drawCentredString(pw / 2, vy, label)

        c.save()
        buf.seek(0)
        from pypdf import PdfReader as PR2
        page.merge_page(PR2(buf).pages[0])
        writer.add_page(page)

    fname, fpath = _overlay_path(upload_folder)
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath


# ───────────────────────────────────────────────────────────────────────────
# White-Out (cover area with white rectangle)
# ───────────────────────────────────────────────────────────────────────────

def whiteout(pdf_path: str, x: float, y: float, w_pct: float, h_pct: float,
             pages: list[int] | None, upload_folder: str) -> tuple[str, str]:
    """Cover a region with a white rectangle (redaction-lite)."""
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
            pw, ph = _page_size_pts(page)
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(pw, ph))
            c.setFillColorRGB(1, 1, 1)
            c.setStrokeColorRGB(1, 1, 1)
            rx, ry = pw * (x / 100.0), ph * (y / 100.0)
            rw, rh = pw * (w_pct / 100.0), ph * (h_pct / 100.0)
            c.rect(rx, ry, rw, rh, fill=1, stroke=0)
            c.save()

            buf.seek(0)
            from pypdf import PdfReader as PR2
            page.merge_page(PR2(buf).pages[0])

        writer.add_page(page)

    fname, fpath = _overlay_path(upload_folder)
    with open(fpath, 'wb') as f:
        writer.write(f)
    writer.close()
    return fname, fpath
