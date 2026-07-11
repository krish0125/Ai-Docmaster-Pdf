import fitz
import os
import pdfplumber

def map_font(family, bold, italic):
    family = (family or "helvetica").lower()
    if "times" in family:
        base = "Times"
    elif "cour" in family:
        base = "Courier"
    else:
        base = "Helvetica"
        
    if bold and italic:
        suffix = "-BoldOblique" if base in ("Helvetica", "Courier") else "-BoldItalic"
    elif bold:
        suffix = "-Bold"
    elif italic:
        suffix = "-Oblique" if base in ("Helvetica", "Courier") else "-Italic"
    else:
        suffix = ""
        
    if base == "Times" and suffix == "":
        return "Times-Roman"
    return base + suffix

def apply_edits_new(src_pdf, dest_pdf, edits):
    doc = fitz.open(src_pdf)
    
    # Group edits by page
    edits_by_page = {}
    for edit in edits:
        p_idx = int(edit.get("page_index", 0))
        edits_by_page.setdefault(p_idx, []).append(edit)
        
    for page_index, page_edits in edits_by_page.items():
        if page_index < 0 or page_index >= len(doc):
            continue
        page = doc[page_index]
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Get rawdict for matching original spans/chars
        page_dict = page.get_text("rawdict")
        
        redact_rects = []
        text_insertions = []
        
        for edit in page_edits:
            x = float(edit.get('x', 0)) * page_width
            y = float(edit.get('y', 0)) * page_height
            w = float(edit.get('width', 0)) * page_width
            h = float(edit.get('height', 0)) * page_height
            
            rect = fitz.Rect(x, y, x + w, y + h)
            edit_type = edit.get('type', 'edit')
            
            text = edit.get('text', '')
            font_family = edit.get('font_family', 'Helvetica')
            font_size = float(edit.get('font_size', 12))
            bold = bool(edit.get('bold', False))
            italic = bool(edit.get('italic', False))
            font_name = map_font(font_family, bold, italic)
            
            hex_color = edit.get('color', '#000000').lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                color = (r, g, b)
            else:
                color = (0, 0, 0)
                
            align_str = edit.get('align', 'left').lower()
            align_code = 0
            if align_str == 'center':
                align_code = 1
            elif align_str == 'right':
                align_code = 2
                
            extra_h = max(h, font_size * 2.0)
            
            if edit_type != 'edit':
                # For non-replacements (i.e. adding new text), fallback to original behavior
                rect_text = fitz.Rect(x, y, x + w, y + extra_h)
                text_insertions.append({
                    "rect": rect_text,
                    "text": text,
                    "font_name": font_name,
                    "font_size": font_size,
                    "color": color,
                    "align": align_code
                })
                continue
                
            # Find matching span for replacement edit
            best_span = None
            max_overlap = 0.0
            for block in page_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        span_rect = fitz.Rect(span["bbox"])
                        intersect = rect & span_rect
                        if not intersect.is_empty:
                            area = intersect.get_area()
                            if area > max_overlap:
                                max_overlap = area
                                best_span = span
                                
            matched = False
            if best_span is not None and "chars" in best_span:
                # Find characters inside the edit rect
                target_indices = []
                for idx, char in enumerate(best_span["chars"]):
                    c_rect = fitz.Rect(char["bbox"])
                    cx = (c_rect.x0 + c_rect.x1) / 2.0
                    cy = (c_rect.y0 + c_rect.y1) / 2.0
                    # Check if character center is inside the edit rect (with a tolerance)
                    if (rect.x0 - 1.0 <= cx <= rect.x1 + 1.0) and (rect.y0 - 2.0 <= cy <= rect.y1 + 2.0):
                        target_indices.append(idx)
                        
                if target_indices:
                    i_start = min(target_indices)
                    i_end = max(target_indices)
                    
                    left_text = "".join(best_span["chars"][i]["c"] for i in range(i_start))
                    right_text = "".join(best_span["chars"][i]["c"] for i in range(i_end + 1, len(best_span["chars"])))
                    
                    new_line_text = left_text + text + right_text
                    
                    # Redact the ENTIRE span bounding box
                    redact_rects.append(fitz.Rect(best_span["bbox"]))
                    
                    # Draw new line text starting at original span's left x and top y
                    start_x = best_span["bbox"][0]
                    # We can use the original span's top y, or edit's y
                    start_y = best_span["bbox"][1]
                    
                    # Determine font size: use edit font size if it is different from default (12), otherwise keep original span size
                    draw_size = font_size
                    if font_size == 12.0 and best_span.get("size"):
                        draw_size = best_span["size"]
                        
                    # Determine font name: keep original span font style if edit font name is default
                    draw_font = font_name
                    # (optional matching or just use draw_font)
                    
                    rect_text = fitz.Rect(start_x, start_y, page_width - 10.0, start_y + draw_size * 3.0)
                    
                    text_insertions.append({
                        "rect": rect_text,
                        "text": new_line_text,
                        "font_name": draw_font,
                        "font_size": draw_size,
                        "color": color,
                        "align": align_code
                    })
                    span_text = "".join(c["c"] for c in best_span["chars"])
                    print(f"Matched span: {span_text} -> Replaced with: {new_line_text}")
                    matched = True
                    
            if not matched:
                # Fallback to original behavior
                redact_rects.append(rect)
                rect_text = fitz.Rect(x, y, max(x + w, page_width - 10.0), y + extra_h)
                text_insertions.append({
                    "rect": rect_text,
                    "text": text,
                    "font_name": font_name,
                    "font_size": font_size,
                    "color": color,
                    "align": align_code
                })
                print("Fallback to normal redaction")
                
        # 1. Apply all redactions
        for r_rect in redact_rects:
            page.add_redact_annot(r_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 2. Insert all new text boxes
        for item in text_insertions:
            if item["text"]:
                overflow = page.insert_textbox(
                    item["rect"],
                    item["text"],
                    fontsize=item["font_size"],
                    fontname=item["font_name"],
                    color=item["color"],
                    align=item["align"]
                )
                if overflow > 0:
                    print(f"WARNING: {overflow} chars not placed in textbox: {item['text']}")
                    
    doc.save(dest_pdf)
    doc.close()

# Let's run Test 1 and Test 2
src_pdf = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures\sample_1page.pdf"
dest1 = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\prototype_output_1.pdf"
dest2 = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\prototype_output_2.pdf"

edits1 = [
    {
        "id": "text-node-0",
        "page_index": 0,
        "type": "edit",
        "x": 0.131,
        "y": 0.091,
        "width": 0.107,
        "height": 0.029,
        "text": "VERIFY-FIX-TEST-12345",
        "font_family": "Helvetica",
        "font_size": 12,
        "color": "#000000",
        "bold": False,
        "italic": False,
        "align": "left"
    }
]

edits2 = [
    {
        "id": "text-node-1",
        "page_index": 0,
        "type": "edit",
        "x": 0.247,
        "y": 0.091,
        "width": 0.060,
        "height": 0.029,
        "text": "VERIFY-FIX-TEST-67890",
        "font_family": "Helvetica",
        "font_size": 12,
        "color": "#000000",
        "bold": False,
        "italic": False,
        "align": "left"
    }
]

print("=== Running Prototype Test 1 ===")
apply_edits_new(src_pdf, dest1, edits1)
with pdfplumber.open(dest1) as pdf:
    text1 = pdf.pages[0].extract_text()
print("Extracted Text 1:")
print(text1)
found1 = "VERIFY-FIX-TEST-12345" in text1
print(f"VERIFY-FIX-TEST-12345 found: {found1}")

print("\n=== Running Prototype Test 2 ===")
apply_edits_new(src_pdf, dest2, edits2)
with pdfplumber.open(dest2) as pdf:
    text2 = pdf.pages[0].extract_text()
print("Extracted Text 2:")
print(text2)
found2 = "VERIFY-FIX-TEST-67890" in text2
print(f"VERIFY-FIX-TEST-67890 found: {found2}")
