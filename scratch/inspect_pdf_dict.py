import fitz
import json

pdf_path = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures\sample_1page.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

text_dict = page.get_text("dict")
print(json.dumps(text_dict, indent=2))
doc.close()
