import os
import fitz

def find_pdf_with_text():
    folder = r"C:\Users\kishu\Desktop\Ai Docmaster\backend\uploads"
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            path = os.path.join(folder, file)
            try:
                doc = fitz.open(path)
                for i in range(len(doc)):
                    text = doc[i].get_text().strip()
                    if text:
                        print(f"Found text in {file} (page {i}): {len(text)} chars")
                        print(text[:200])
                        doc.close()
                        return path
                doc.close()
            except Exception as e:
                pass
    print("No PDF with text found")
    return None

if __name__ == "__main__":
    find_pdf_with_text()
