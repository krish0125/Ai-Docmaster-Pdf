import fitz
import os

pdf_path = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures\sample_1page.pdf"
doc = fitz.open(pdf_path)
page = doc[0]

print("Page Rect:", page.rect)
print("\n--- Words ---")
for word in page.get_text("words"):
    print(word)

print("\n--- Text Blocks/Lines/Spans ---")
print(page.get_text("text"))
doc.close()
