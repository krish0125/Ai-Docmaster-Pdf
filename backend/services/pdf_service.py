"""PDF processing service — merge, split, compress, extract text.

Uses pypdf (NOT the deprecated PyPDF2) and pdfplumber for text extraction.
"""

import os
from pypdf import PdfReader, PdfWriter
import pdfplumber


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_text(file_path: str) -> str:
    """Extract text from every page of a PDF using pdfplumber.

    Falls back to pypdf if pdfplumber fails for a page.
    """
    text_parts: list[str] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        print(f"[PDFService] pdfplumber extraction failed, trying pypdf: {e}")

    # Fallback / supplement with pypdf if pdfplumber yielded nothing
    if not text_parts:
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        except Exception as e:
            print(f"[PDFService] pypdf extraction also failed: {e}")

    return '\n\n'.join(text_parts)


# ---------------------------------------------------------------------------
# PDF info
# ---------------------------------------------------------------------------

def get_pdf_info(file_path: str) -> dict:
    """Return basic metadata about a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = extract_text(file_path)
        return {
            'page_count': len(reader.pages),
            'file_size': os.path.getsize(file_path),
            'has_text': len(text.strip()) > 0,
        }
    except Exception as e:
        return {'error': str(e), 'page_count': 0, 'file_size': 0, 'has_text': False}


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge_pdfs(file_paths: list[str], output_path: str) -> str:
    """Merge multiple PDFs into one using PdfWriter.append().

    Returns the output file path.
    """
    writer = PdfWriter()
    for path in file_paths:
        writer.append(path)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------

def parse_page_ranges(ranges_str: str, total_pages: int) -> list[list[int]]:
    """Parse a human-friendly range string like ``"1-3,5,7-10"`` into a list
    of *groups*, where each group is a list of **0-indexed** page numbers.

    Each comma-separated token becomes its own group so the caller can
    produce one output file per group.
    """
    groups: list[list[int]] = []
    for part in ranges_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            tokens = part.split('-', 1)
            start = int(tokens[0].strip()) - 1  # convert to 0-indexed
            end = int(tokens[1].strip()) - 1
            start = max(0, start)
            end = min(total_pages - 1, end)
            groups.append(list(range(start, end + 1)))
        else:
            page_num = int(part.strip()) - 1
            if 0 <= page_num < total_pages:
                groups.append([page_num])
    return groups


def split_pdf(file_path: str, page_ranges: str, output_dir: str) -> list[str]:
    """Split a PDF by *page_ranges* (e.g. ``"1-3,5,7-10"``).

    Returns a list of output file paths (one per range group).
    """
    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    groups = parse_page_ranges(page_ranges, total_pages)

    os.makedirs(output_dir, exist_ok=True)
    output_paths: list[str] = []

    base_name = os.path.splitext(os.path.basename(file_path))[0]

    for idx, page_nums in enumerate(groups, start=1):
        writer = PdfWriter()
        for pn in page_nums:
            writer.add_page(reader.pages[pn])
        out_name = f"{base_name}_part{idx}.pdf"
        out_path = os.path.join(output_dir, out_name)
        with open(out_path, 'wb') as f:
            writer.write(f)
        writer.close()
        output_paths.append(out_path)

    return output_paths


# ---------------------------------------------------------------------------
# Compress
# ---------------------------------------------------------------------------

def compress_pdf(file_path: str, output_path: str) -> dict:
    """Compress a PDF by removing duplicate objects and compressing streams.

    Returns a dict with size statistics.
    """
    original_size = os.path.getsize(file_path)

    reader = PdfReader(file_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Apply compression
    writer.compress_identical_objects(
        remove_identicals=True,
        remove_orphans=True,
    )
    for page in writer.pages:
        page.compress_content_streams(level=9)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()

    compressed_size = os.path.getsize(output_path)
    reduction = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0

    return {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'reduction_percent': round(reduction, 2),
    }


# ---------------------------------------------------------------------------
# Organize / Reorder pages
# ---------------------------------------------------------------------------

def organize_pdf(file_path: str, page_order: list[int], output_path: str) -> str:
    """Reorder pages according to *page_order* (1-indexed list).

    Example: [3, 1, 2] puts page 3 first, then 1, then 2.
    Returns the output file path.
    """
    reader = PdfReader(file_path)
    total = len(reader.pages)
    writer = PdfWriter()

    for page_num in page_order:
        idx = page_num - 1  # convert to 0-indexed
        if 0 <= idx < total:
            writer.add_page(reader.pages[idx])

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Rotate pages
# ---------------------------------------------------------------------------

def rotate_pdf(file_path: str, rotation: int, pages: list[int] | None,
               output_path: str) -> str:
    """Rotate *pages* (1-indexed) by *rotation* degrees (90, 180, or 270).

    If *pages* is None or empty, all pages are rotated.
    Returns the output file path.
    """
    if rotation not in (90, 180, 270):
        raise ValueError(f'Invalid rotation {rotation}. Must be 90, 180, or 270.')

    reader = PdfReader(file_path)
    writer = PdfWriter()
    total = len(reader.pages)

    # Normalise to 0-indexed set; empty means all pages
    target = set()
    if pages:
        for p in pages:
            idx = p - 1
            if 0 <= idx < total:
                target.add(idx)
    else:
        target = set(range(total))

    for idx, page in enumerate(reader.pages):
        if idx in target:
            page.rotate(rotation)
        writer.add_page(page)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Delete pages
# ---------------------------------------------------------------------------

def delete_pages(file_path: str, pages_to_delete: list[int],
                 output_path: str) -> str:
    """Delete the specified pages (1-indexed) from the PDF.

    Returns the output file path.
    """
    reader = PdfReader(file_path)
    total = len(reader.pages)
    writer = PdfWriter()

    # Build 0-indexed set of pages to remove
    delete_set = set()
    for p in pages_to_delete:
        idx = p - 1
        if 0 <= idx < total:
            delete_set.add(idx)

    for idx, page in enumerate(reader.pages):
        if idx not in delete_set:
            writer.add_page(page)

    if len(writer.pages) == 0:
        raise ValueError('All pages would be deleted — at least one page must remain.')

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Extract pages (single-output version of split)
# ---------------------------------------------------------------------------

def extract_pages(file_path: str, pages: list[int], output_path: str) -> str:
    """Extract specific pages (1-indexed) into a single output PDF.

    Unlike split_pdf which produces one file per range group, this
    always produces exactly one output file.
    Returns the output file path.
    """
    reader = PdfReader(file_path)
    total = len(reader.pages)
    writer = PdfWriter()

    for p in pages:
        idx = p - 1
        if 0 <= idx < total:
            writer.add_page(reader.pages[idx])

    if len(writer.pages) == 0:
        raise ValueError('No valid page numbers provided.')

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Duplicate pages
# ---------------------------------------------------------------------------

def duplicate_pages(file_path: str, pages: list[int], output_path: str) -> str:
    """Append duplicates of *pages* (1-indexed) to the end of the PDF.

    Returns the output file path with the duplicated pages appended.
    """
    reader = PdfReader(file_path)
    total = len(reader.pages)
    writer = PdfWriter()

    # First, copy all original pages
    for page in reader.pages:
        writer.add_page(page)

    # Then append duplicates of the requested pages
    for p in pages:
        idx = p - 1
        if 0 <= idx < total:
            writer.add_page(reader.pages[idx])

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Crop pages
# ---------------------------------------------------------------------------

def crop_pdf(file_path: str, left: float, bottom: float, right: float,
             top: float, pages: list[int] | None, output_path: str) -> str:
    """Crop pages by adjusting the MediaBox (PDF user-space units, 1 pt = 1/72 in).

    *left*, *bottom*, *right*, *top* are expressed as **percentages** (0-100)
    of the original page dimensions, which makes this device-agnostic.

    If *pages* is None or empty, all pages are cropped.
    Returns the output file path.
    """
    reader = PdfReader(file_path)
    total = len(reader.pages)
    writer = PdfWriter()

    target = set(range(total)) if not pages else {p - 1 for p in pages if 0 <= p - 1 < total}

    for idx, page in enumerate(reader.pages):
        if idx in target:
            mb = page.mediabox
            w = float(mb.width)
            h = float(mb.height)
            new_left   = mb.left   + w * (left   / 100.0)
            new_bottom = mb.bottom + h * (bottom / 100.0)
            new_right  = mb.left   + w * (right  / 100.0)
            new_top    = mb.bottom + h * (top    / 100.0)
            page.mediabox.left   = new_left
            page.mediabox.bottom = new_bottom
            page.mediabox.right  = new_right
            page.mediabox.top    = new_top
        writer.add_page(page)

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        writer.write(f)
    writer.close()
    return output_path


# ---------------------------------------------------------------------------
# Rearrange (drag-and-drop new order)
# ---------------------------------------------------------------------------

def rearrange_pdf(file_path: str, new_order: list[int], output_path: str) -> str:
    """Rearrange all pages into the given *new_order* (1-indexed permutation).

    This is an alias of organize_pdf with stricter validation: the length of
    *new_order* must equal the total number of pages and must be a permutation.
    Returns the output file path.
    """
    reader = PdfReader(file_path)
    total = len(reader.pages)

    if len(new_order) != total:
        raise ValueError(
            f'new_order has {len(new_order)} entries but the PDF has {total} pages. '
            'Provide exactly one entry per page.'
        )

    # validate it is a permutation of 1..total
    if sorted(new_order) != list(range(1, total + 1)):
        raise ValueError(
            f'new_order must be a permutation of pages 1 to {total}.'
        )

    return organize_pdf(file_path, new_order, output_path)
