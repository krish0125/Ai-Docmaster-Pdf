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

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
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

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
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
