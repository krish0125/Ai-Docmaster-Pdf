import os
import fitz
import pdfplumber

def test_edit_redact():
    fixture_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures"
    src = os.path.join(fixture_dir, "sample_1page.pdf")
    dest = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\output_redact.pdf"
    
    print(f"Loading {src}...")
    doc = fitz.open(src)
    page = doc[0]
    
    # Search for text
    text_to_find = "Sample"
    rects = page.search_for(text_to_find)
    print(f"Text to find: '{text_to_find}', Rects: {rects}")
    
    if rects:
        r = rects[0]
        # Redact the original text bounding box
        page.add_redact_annot(r)
        page.apply_redactions()
        print("Applied redactions!")
        
        # Write new text
        new_text = "EDITED-TEXT-NOW"
        font_size = 12
        font_name = "Helvetica"
        color = (0, 0, 0)
        
        # Calculate expanded box as in route
        extra_h = max(r.height, font_size * 2.0)
        rect_text = fitz.Rect(r.x0, r.y0, max(r.x0 + r.width, page.rect.width - 10.0), r.y0 + extra_h)
        
        overflow = page.insert_textbox(rect_text, new_text, fontsize=font_size, fontname=font_name, color=color, align=0)
        print(f"Insert textbox overflow: {overflow}")
        
    doc.save(dest)
    doc.close()
    print(f"Saved to {dest}")
    
    # Read text back with pdfplumber
    print("Reading text back via pdfplumber...")
    with pdfplumber.open(dest) as pdf:
        txt = pdf.pages[0].extract_text()
        print("--- EXTRACTED TEXT ---")
        print(txt)
        print("----------------------")
        if "EDITED-TEXT-NOW" in txt:
            print("SUCCESS: EDITED-TEXT-NOW found in output!")
        else:
            print("FAILURE: EDITED-TEXT-NOW not found in output!")
            
        if text_to_find in txt:
            print(f"WARNING: Original text '{text_to_find}' is still present in text extraction!")
        else:
            print(f"SUCCESS: Original text '{text_to_find}' was successfully removed/hidden!")

if __name__ == "__main__":
    test_edit_redact()
