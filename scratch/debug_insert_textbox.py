import fitz
import os

def debug():
    fixture_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures"
    src = os.path.join(fixture_dir, "sample_1page.pdf")
    dest = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\debug_output.pdf"
    
    doc = fitz.open(src)
    page = doc[0]
    
    # We will simulate the exact values from the Flask route for "Sample":
    # edits passed:
    # "x": 0.131, "y": 0.091, "width": 0.107, "height": 0.028
    page_width = page.rect.width
    page_height = page.rect.height
    
    x = 0.131 * page_width
    y = 0.091 * page_height
    w = 0.107 * page_width
    h = 0.028 * page_height
    
    rect = fitz.Rect(x, y, x + w, y + h)
    
    # 1. draw rect
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
    
    # 2. insert textbox
    text = "PRACTICAL-2-EDITED-TEST"
    font_family = "Helvetica"
    font_size = 12.0
    bold = False
    italic = False
    
    # map font
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
        
    font_name = map_font(font_family, bold, italic)
    color = (0, 0, 0)
    align_code = 0
    
    extra_h = max(h, font_size * 2.0)
    rect_text = fitz.Rect(x, y, max(x + w, page_width - 10.0), y + extra_h)
    
    print(f"rect_text: {rect_text}")
    print(f"text: {text}")
    print(f"fontsize: {font_size}")
    print(f"fontname: {font_name}")
    print(f"color: {color}")
    print(f"align_code: {align_code}")
    
    try:
        overflow = page.insert_textbox(rect_text, text, fontsize=font_size, fontname=font_name, color=color, align=align_code)
        print(f"Success! Overflow: {overflow}")
    except Exception as e:
        print(f"Exception during insert_textbox: {e}")
        
    doc.save(dest)
    doc.close()
    
    # Let's inspect text
    doc2 = fitz.open(dest)
    print("Words in output:")
    for w in doc2[0].get_text("words"):
        print(w)
    doc2.close()

if __name__ == "__main__":
    debug()
