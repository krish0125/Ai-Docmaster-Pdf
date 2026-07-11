# test_audit.py
import os
import requests
import json
import traceback

BASE = "http://localhost:5001"
FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')

# Register a temporary user
test_email = "audit_user@test.com"
test_pass = "auditpass123"
token = ""

def get_token():
    global token
    try:
        # Check login first
        r = requests.post(f"{BASE}/auth/login", json={"email": test_email, "password": test_pass})
        if r.status_code == 200:
            token = r.json()['token']
            return
        # If not, signup
        requests.post(f"{BASE}/auth/signup", json={"name": "Audit User", "email": test_email, "password": test_pass})
        r = requests.post(f"{BASE}/auth/login", json={"email": test_email, "password": test_pass})
        token = r.json()['token']
    except Exception as e:
        print(f"Auth setup failed: {e}")

get_token()
headers = {"Authorization": f"Bearer {token}"}

results = []

def log_test(tool_name, route, status, err_msg="", root_cause=""):
    results.append({
        "tool": tool_name,
        "route": route,
        "status": status,
        "error": err_msg,
        "cause": root_cause
    })
    print(f"{tool_name} | {route} | {status} | {err_msg[:40]}")

# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
def upload_test(route, filename, files_dict, data_dict=None):
    fpath = os.path.join(FIXTURES, filename)
    if not os.path.isfile(fpath):
        return None, f"Fixture not found: {filename}"
    
    opened_files = {}
    for key, name in files_dict.items():
        opened_files[key] = open(os.path.join(FIXTURES, name), 'rb')
        
    try:
        r = requests.post(f"{BASE}{route}", headers=headers, files=opened_files, data=data_dict)
        return r, ""
    except Exception as e:
        return None, str(e)
    finally:
        for f in opened_files.values():
            f.close()

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: PDF Management
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 1: PDF Management ---")

r, err = upload_test("/pdf/upload", "sample_1page.pdf", {"file": "sample_1page.pdf"})
if r and r.status_code in (200, 201):
    log_test("Upload PDF", "/pdf/upload", "pass")
else:
    log_test("Upload PDF", "/pdf/upload", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Merge
f1 = open(os.path.join(FIXTURES, "sample_1page.pdf"), 'rb')
f2 = open(os.path.join(FIXTURES, "sample_1page.pdf"), 'rb')
try:
    r = requests.post(f"{BASE}/pdf/merge", headers=headers, files=[("files", f1), ("files", f2)])
    if r.status_code == 200:
        log_test("Merge PDFs", "/pdf/merge", "pass")
    else:
        log_test("Merge PDFs", "/pdf/merge", "fail", f"HTTP {r.status_code}", r.text)
except Exception as e:
    log_test("Merge PDFs", "/pdf/merge", "fail", str(e))
finally:
    f1.close(); f2.close()

# Split
r, err = upload_test("/pdf/split", "sample_5page.pdf", {"file": "sample_5page.pdf"}, {"pages": "1-2,3"})
if r and r.status_code == 200:
    log_test("Split PDF", "/pdf/split", "pass")
else:
    log_test("Split PDF", "/pdf/split", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Compress
r, err = upload_test("/pdf/compress", "sample_5page.pdf", {"file": "sample_5page.pdf"})
if r and r.status_code == 200:
    log_test("Compress PDF", "/pdf/compress", "pass")
else:
    log_test("Compress PDF", "/pdf/compress", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Rotate
r, err = upload_test("/pdf/rotate", "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"rotation": "90"})
if r and r.status_code == 200:
    log_test("Rotate PDF", "/pdf/rotate", "pass")
else:
    log_test("Rotate PDF", "/pdf/rotate", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Delete pages
r, err = upload_test("/pdf/delete-pages", "sample_5page.pdf", {"file": "sample_5page.pdf"}, {"pages": "1,3"})
if r and r.status_code == 200:
    log_test("Delete Pages", "/pdf/delete-pages", "pass")
else:
    log_test("Delete Pages", "/pdf/delete-pages", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Extract pages
r, err = upload_test("/pdf/extract-pages", "sample_5page.pdf", {"file": "sample_5page.pdf"}, {"pages": "1,2"})
if r and r.status_code == 200:
    log_test("Extract Pages", "/pdf/extract-pages", "pass")
else:
    log_test("Extract Pages", "/pdf/extract-pages", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Duplicate pages
r, err = upload_test("/pdf/duplicate-pages", "sample_5page.pdf", {"file": "sample_5page.pdf"}, {"pages": "1,2"})
if r and r.status_code == 200:
    log_test("Duplicate Pages", "/pdf/duplicate-pages", "pass")
else:
    log_test("Duplicate Pages", "/pdf/duplicate-pages", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Crop PDF
r, err = upload_test("/pdf/crop", "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"left": "10", "bottom": "10", "right": "90", "top": "90"})
if r and r.status_code == 200:
    log_test("Crop PDF", "/pdf/crop", "pass")
else:
    log_test("Crop PDF", "/pdf/crop", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Rearrange
r, err = upload_test("/pdf/rearrange", "sample_5page.pdf", {"file": "sample_5page.pdf"}, {"new_order": "5,4,3,2,1"})
if r and r.status_code == 200:
    log_test("Rearrange Pages", "/pdf/rearrange", "pass")
else:
    log_test("Rearrange Pages", "/pdf/rearrange", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

# Organize
r, err = upload_test("/pdf/organize", "sample_5page.pdf", {"file": "sample_5page.pdf"}, {"page_order": "1,3,5"})
if r and r.status_code == 200:
    log_test("Organize Pages", "/pdf/organize", "pass")
else:
    log_test("Organize Pages", "/pdf/organize", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: PDF Conversion
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 2: PDF Conversion ---")

conversions = [
    ("PDF to Word", "/convert/pdf-to-word", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("Word to PDF", "/convert/word-to-pdf", "sample.docx", {"file": "sample.docx"}),
    ("PDF to Excel", "/convert/pdf-to-excel", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("Excel to PDF", "/convert/excel-to-pdf", "sample.xlsx", {"file": "sample.xlsx"}),
    ("PDF to PPTX", "/convert/pdf-to-pptx", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("PDF to Image", "/convert/pdf-to-image", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("PDF to HTML", "/convert/pdf-to-html", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("PDF to Text", "/convert/pdf-to-text", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("PDF to EPUB", "/convert/pdf-to-epub", "sample_1page.pdf", {"file": "sample_1page.pdf"}),
    ("Image to PDF", "/convert/image-to-pdf", "sample.png", {"file": "sample.png"}),
    ("Text to PDF", "/convert/text-to-pdf", "sample.txt", {"file": "sample.txt"}),
    ("EPUB to PDF", "/convert/epub-to-pdf", "sample.epub", {"file": "sample.epub"}),
]

for name, route, fixture, files in conversions:
    r, err = upload_test(route, fixture, files)
    if r and r.status_code == 200:
        log_test(name, route, "pass")
    else:
        log_test(name, route, "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: PDF Editing
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 3: PDF Editing ---")

r, err = upload_test("/edit/add-text", "sample_1page.pdf", {"file": "sample_1page.pdf"},
                     {"text": "Sample Stamp", "x": "10", "y": "10", "font_size": "12", "color": "#000000"})
if r and r.status_code == 200:
    log_test("Add Text Overlay", "/edit/add-text", "pass")
else:
    log_test("Add Text Overlay", "/edit/add-text", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/edit/add-image", "sample_1page.pdf", {"file": "sample_1page.pdf", "image": "sample.png"},
                     {"x": "50", "y": "50", "width": "20"})
if r and r.status_code == 200:
    log_test("Add Image Stamp", "/edit/add-image", "pass")
else:
    log_test("Add Image Stamp", "/edit/add-image", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/edit/highlight", "sample_1page.pdf", {"file": "sample_1page.pdf"},
                     {"x": "10", "y": "10", "width": "50", "height": "20", "color": "#FFFF00", "opacity": "0.4"})
if r and r.status_code == 200:
    log_test("Highlight Area", "/edit/highlight", "pass")
else:
    log_test("Highlight Area", "/edit/highlight", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/edit/header-footer", "sample_1page.pdf", {"file": "sample_1page.pdf"},
                     {"header": "My Header", "footer": "My Footer", "font_size": "10"})
if r and r.status_code == 200:
    log_test("Header & Footer", "/edit/header-footer", "pass")
else:
    log_test("Header & Footer", "/edit/header-footer", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/edit/page-numbers", "sample_1page.pdf", {"file": "sample_1page.pdf"},
                     {"position": "bottom-center", "font_size": "10", "start": "1"})
if r and r.status_code == 200:
    log_test("Page Numbers", "/edit/page-numbers", "pass")
else:
    log_test("Page Numbers", "/edit/page-numbers", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/edit/whiteout", "sample_1page.pdf", {"file": "sample_1page.pdf"},
                     {"x": "10", "y": "10", "width": "30", "height": "10"})
if r and r.status_code == 200:
    log_test("Whiteout area", "/edit/whiteout", "pass")
else:
    log_test("Whiteout area", "/edit/whiteout", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: PDF Security
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 4: PDF Security ---")

r, err = upload_test("/security/lock", "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"password": "pwd123"})
if r and r.status_code == 200:
    log_test("Lock PDF", "/security/lock", "pass")
else:
    log_test("Lock PDF", "/security/lock", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/security/watermark", "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"text": "DRAFT"})
if r and r.status_code == 200:
    log_test("Watermark PDF", "/security/watermark", "pass")
else:
    log_test("Watermark PDF", "/security/watermark", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/security/flatten", "sample_1page.pdf", {"file": "sample_1page.pdf"})
if r and r.status_code == 200:
    log_test("Flatten PDF", "/security/flatten", "pass")
else:
    log_test("Flatten PDF", "/security/flatten", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/security/remove-metadata", "sample_1page.pdf", {"file": "sample_1page.pdf"})
if r and r.status_code == 200:
    log_test("Remove Metadata", "/security/remove-metadata", "pass")
else:
    log_test("Remove Metadata", "/security/remove-metadata", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/security/sign", "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"signer_name": "Test Signer"})
if r and r.status_code == 200:
    log_test("Digital Stamp Signature", "/security/sign", "pass")
else:
    log_test("Digital Stamp Signature", "/security/sign", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/security/redact", "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"x": "10", "y": "40", "width": "30", "height": "5"})
if r and r.status_code == 200:
    log_test("Redaction", "/security/redact", "pass")
else:
    log_test("Redaction", "/security/redact", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: OCR & Scanner
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 5: OCR & Scanner ---")

r, err = upload_test("/ocr/extract", "sample.png", {"file": "sample.png"})
if r and r.status_code == 200:
    log_test("Standard OCR", "/ocr/extract", "pass")
else:
    log_test("Standard OCR", "/ocr/extract", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/ocr/handwriting", "sample.png", {"file": "sample.png"})
if r and r.status_code == 200:
    log_test("Handwriting OCR", "/ocr/handwriting", "pass")
else:
    log_test("Handwriting OCR", "/ocr/handwriting", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/ocr/extract-tables", "sample_1page.pdf", {"file": "sample_1page.pdf"})
if r and r.status_code == 200:
    log_test("Extract Tables", "/ocr/extract-tables", "pass")
else:
    log_test("Extract Tables", "/ocr/extract-tables", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/ocr/extract-images", "sample_1page.pdf", {"file": "sample_1page.pdf"})
if r and r.status_code == 200:
    log_test("Extract Images", "/ocr/extract-images", "pass")
else:
    log_test("Extract Images", "/ocr/extract-images", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/ocr/multilang-ocr", "sample.png", {"file": "sample.png"}, {"lang": "eng"})
if r and r.status_code == 200:
    log_test("Multilingual OCR", "/ocr/multilang-ocr", "pass")
else:
    log_test("Multilingual OCR", "/ocr/multilang-ocr", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: AI Engines
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 6: AI Engines ---")

ai_tools = [
    ("Explain PDF", "/ai/explain"),
    ("Keywords Indexing", "/ai/keywords"),
    ("Generate Quiz", "/ai/quiz"),
    ("Generate MCQ", "/ai/mcq"),
    ("Grammar Check", "/ai/check-grammar"),
    ("Improve Writing", "/ai/improve-writing"),
    ("Proofread Document", "/ai/proofread"),
    ("Translate", "/ai/translate"),
    ("Rewrite", "/ai/rewrite"),
    ("Change Tone", "/ai/change-tone"),
    ("Analyze Contract", "/ai/analyze-contract"),
    ("Read Invoice", "/ai/read-invoice"),
    ("Analyze Financials", "/ai/analyze-financial"),
    ("Review Legal Docs", "/ai/review-legal"),
    ("Assignment Helper", "/ai/assignment-helper"),
    ("Research Assistant", "/ai/research-assistant"),
    ("Cite Sources", "/ai/cite-sources"),
    ("Cover Letter Writer", "/ai/cover-letter"),
    ("Interview Preparation", "/ai/interview-questions"),
]

for name, route in ai_tools:
    # Most AI tools take simple PDF upload or form fields
    r, err = upload_test(route, "sample_1page.pdf", {"file": "sample_1page.pdf"}, {"text": "Sample text for direct raw test"})
    if r and r.status_code == 200:
        log_test(name, route, "pass")
    else:
        log_test(name, route, "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7: Image Tools
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 7: Image Tools ---")

r, err = upload_test("/image/resize", "sample.png", {"file": "sample.png"}, {"width": "100", "height": "100"})
if r and r.status_code == 200:
    log_test("Resize Image", "/image/resize", "pass")
else:
    log_test("Resize Image", "/image/resize", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/convert-format", "sample.png", {"file": "sample.png"}, {"format": "jpg"})
if r and r.status_code == 200:
    log_test("Convert Format", "/image/convert-format", "pass")
else:
    log_test("Convert Format", "/image/convert-format", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/filter", "sample.png", {"file": "sample.png"}, {"filter": "grayscale"})
if r and r.status_code == 200:
    log_test("Apply Filters", "/image/filter", "pass")
else:
    log_test("Apply Filters", "/image/filter", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/remove-background", "sample.png", {"file": "sample.png"})
if r and r.status_code == 200:
    log_test("Remove Background", "/image/remove-background", "pass")
else:
    log_test("Remove Background", "/image/remove-background", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/crop", "sample.png", {"file": "sample.png"}, {"left": "10", "top": "10", "right": "100", "bottom": "100"})
if r and r.status_code == 200:
    log_test("Crop Image", "/image/crop", "pass")
else:
    log_test("Crop Image", "/image/crop", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/rotate", "sample.png", {"file": "sample.png"}, {"angle": "90"})
if r and r.status_code == 200:
    log_test("Rotate Image", "/image/rotate", "pass")
else:
    log_test("Rotate Image", "/image/rotate", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/flip", "sample.png", {"file": "sample.png"}, {"direction": "h"})
if r and r.status_code == 200:
    log_test("Flip Image", "/image/flip", "pass")
else:
    log_test("Flip Image", "/image/flip", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r, err = upload_test("/image/watermark", "sample.png", {"file": "sample.png"}, {"text": "WATERMARK"})
if r and r.status_code == 200:
    log_test("Image Watermark", "/image/watermark", "pass")
else:
    log_test("Image Watermark", "/image/watermark", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8: Utilities
# ─────────────────────────────────────────────────────────────────────────────
print("\n--- Auditing Phase 8: Utilities ---")

r = requests.post(f"{BASE}/utils/qr", headers=headers, json={"data": "http://google.com", "size": 200})
if r.status_code == 200:
    log_test("QR Code Generator", "/utils/qr", "pass")
else:
    log_test("QR Code Generator", "/utils/qr", "fail", f"HTTP {r.status_code}", r.text)

r = requests.post(f"{BASE}/utils/barcode", headers=headers, json={"data": "12345678", "type": "code128"})
if r.status_code == 200:
    log_test("Barcode Generator", "/utils/barcode", "pass")
else:
    log_test("Barcode Generator", "/utils/barcode", "fail", f"HTTP {r.status_code}", r.text)

r, err = upload_test("/utils/pdf-metadata", "sample_1page.pdf", {"file": "sample_1page.pdf"})
if r and r.status_code == 200:
    log_test("PDF Metadata View", "/utils/pdf-metadata", "pass")
else:
    log_test("PDF Metadata View", "/utils/pdf-metadata", "fail", err or f"HTTP {r.status_code if r is not None else 'None'}", r.text if r is not None else "")

r = requests.post(f"{BASE}/utils/password", headers=headers, json={"length": 16, "upper": True, "lower": True, "digits": True, "special": True})
if r.status_code == 200:
    log_test("Password Generator", "/utils/password", "pass")
else:
    log_test("Password Generator", "/utils/password", "fail", f"HTTP {r.status_code}", r.text)

# ─────────────────────────────────────────────────────────────────────────────
# Write checklist
# ─────────────────────────────────────────────────────────────────────────────
checklist_path = os.path.join(os.path.dirname(__file__), 'audit_results.json')
with open(checklist_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print("\n✅ Initial audit run complete. Results written to audit_results.json.")
