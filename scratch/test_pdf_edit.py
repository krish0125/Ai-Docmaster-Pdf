import os
import fitz

def simulate_route_edits():
    pdf_path = r"C:\Users\kishu\Desktop\Ai Docmaster\backend\uploads\01109d0518264f9c85ba4a2d65f87d62_suite.pdf"
    if not os.path.exists(pdf_path):
        print(f"Path does not exist: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    page = doc[0]
    page_width = page.rect.width
    page_height = page.rect.height

    # Simulated edits:
    # 1. Edit block 0 (original width is ~206, we change text to a longer one)
    # block 0 rect: (72.0, 128.98977661132812, 278.0759582519531, 145.47776794433594)
    # So x = 72.0 / page_width, y = 128.9897... / page_height, etc.
    edits = [
        {
            "page_index": 0,
            "type": "edit",
            "x": 72.0 / page_width,
            "y": 128.98977661132812 / page_height,
            "width": (278.0759582519531 - 72.0) / page_width,
            "height": (145.47776794433594 - 128.98977661132812) / page_height,
            "text": "AI DocMaster Edited Text - Page 1 (Much Longer to Test Width Expansion!)",
            "font_family": "Helvetica",
            "font_size": 14.0,
            "color": "#FF0000",
            "bold": True,
            "italic": False,
            "align": "left"
        },
        {
            "page_index": 0,
            "type": "add",
            "x": 100.0 / page_width,
            "y": 300.0 / page_height,
            "width": 150.0 / page_width,
            "height": 30.0 / page_height,
            "text": "Added Custom Textbox",
            "font_family": "Helvetica",
            "font_size": 12.0,
            "color": "#0000FF",
            "bold": False,
            "italic": True,
            "align": "center"
        }
    ]

    for edit in edits:
        # Convert percentage coordinates to PDF points
        x = float(edit.get('x', 0)) * page_width
        y = float(edit.get('y', 0)) * page_height
        w = float(edit.get('width', 0)) * page_width
        h = float(edit.get('height', 0)) * page_height
        
        rect = fitz.Rect(x, y, x + w, y + h)
        edit_type = edit.get('type', 'edit')
        
        # 1. For replacements, white out the original bounding box
        if edit_type == 'edit':
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
        
        # 2. Draw the new text inside the bounding box
        text = edit.get('text', '')
        font_size = float(edit.get('font_size', 12))
        font_name = "hebo" if edit.get('bold') else "helv"
        if edit.get('italic'):
            font_name = "hebi" if edit.get('bold') else "heit"
            
        color = (1.0, 0.0, 0.0) if edit.get('color') == "#FF0000" else (0.0, 0.0, 1.0)
        
        align_str = edit.get('align', 'left').lower()
        align_code = 0
        if align_str == 'center':
            align_code = 1
        elif align_str == 'right':
            align_code = 2

        # Expanded rect calculation
        extra_h = max(h, font_size * 2.0)
        if edit_type == 'edit':
            if align_code == 0:
                rect_text = fitz.Rect(x, y, max(x + w, page_width - 10.0), y + extra_h)
            elif align_code == 1:
                pad_w = 100.0
                new_x0 = max(0.0, x - pad_w / 2.0)
                new_x1 = min(page_width, x + w + pad_w / 2.0)
                rect_text = fitz.Rect(new_x0, y, new_x1, y + extra_h)
            else:
                rect_text = fitz.Rect(10.0, y, max(x + w, page_width - 10.0), y + extra_h)
        else:
            rect_text = fitz.Rect(x, y, x + w, y + extra_h)
            
        if text:
            ret = page.insert_textbox(rect_text, text, fontsize=font_size, fontname=font_name, color=color, align=align_code)
            print(f"insert_textbox for type={edit_type} returned: {ret}")

    out_path = r"C:\Users\kishu\Desktop\Ai Docmaster\scratch\test_output_route.pdf"
    doc.save(out_path)
    doc.close()
    print("Saved simulated output.")

    # Re-open and check text
    doc2 = fitz.open(out_path)
    text_content = doc2[0].get_text()
    print(f"Is 'Much Longer' in output? {'Much Longer' in text_content}")
    print(f"Is 'Added Custom' in output? {'Added Custom' in text_content}")
    doc2.close()

if __name__ == "__main__":
    simulate_route_edits()
