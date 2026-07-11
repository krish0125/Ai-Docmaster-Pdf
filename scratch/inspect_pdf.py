import fitz

def inspect():
    path = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\downloaded_output.pdf"
    doc = fitz.open(path)
    page = doc[0]
    
    print("--- PAGE DRAWINGS ---")
    drawings = page.get_drawings()
    print(f"Number of drawings: {len(drawings)}")
    for d in drawings:
        print(d)
        
    print("\n--- PAGE TEXT WORDS ---")
    words = page.get_text("words")
    print(f"Number of words: {len(words)}")
    for w in words:
        print(w)
        
    doc.close()

if __name__ == "__main__":
    inspect()
