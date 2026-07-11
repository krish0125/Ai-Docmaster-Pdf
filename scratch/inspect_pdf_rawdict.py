import fitz
import json

pdf_path = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures\sample_1page.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

text_rawdict = page.get_text("rawdict")
# Just print the first block to see the structure of spans and chars
if text_rawdict["blocks"]:
    print(json.dumps(text_rawdict["blocks"][0], indent=2))
doc.close()
