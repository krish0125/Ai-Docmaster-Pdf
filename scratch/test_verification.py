import os
import requests
import json
import pdfplumber
import random

def run_verification():
    BASE = "http://localhost:5001"
    
    # Generate unique test credentials
    rand_id = random.randint(1000, 9999)
    email = f"verify_user_{rand_id}@test.com"
    password = "Password123!"
    
    print(f"Signing up new user: {email}...")
    signup_res = requests.post(f"{BASE}/auth/signup", json={
        "name": "Verification User",
        "email": email,
        "password": password
    })
    print(f"Signup Response ({signup_res.status_code}): {signup_res.text}")
    
    login_res = requests.post(f"{BASE}/auth/login", json={
        "email": email,
        "password": password
    })
    print(f"Login Response ({login_res.status_code}): {login_res.text}")
    
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    fixture_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures"
    src_pdf = os.path.join(fixture_dir, "sample_1page.pdf")
    
    # -------------------------------------------------------------
    # TEST 1: Replaces 'Sample' with 'VERIFY-FIX-TEST-12345'
    # 'Sample' is at x=78.0, y=76.74, w=64.0, h=24.8 in sample_1page.pdf
    # Page size: 595.28 x 841.89
    # Ratios: x=0.131, y=0.091, w=0.107, h=0.029
    # -------------------------------------------------------------
    print("\n--- Running Test 1 ---")
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
    
    files = {"file": open(src_pdf, "rb")}
    data = {"edits": json.dumps(edits1)}
    
    r1 = requests.post(f"{BASE}/edit/edit-pdf-text", headers=headers, files=files, data=data)
    files["file"].close()
    
    print(f"Response ({r1.status_code}): {r1.text}")
    if r1.status_code != 200:
        print("Test 1 failed to process edit.")
        return
        
    dl_url = r1.json()["download_url"]
    dl_res = requests.get(f"{BASE}{dl_url}")
    dest1 = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\downloaded_verify_1.pdf"
    with open(dest1, "wb") as f:
        f.write(dl_res.content)
    print(f"Downloaded Test 1 result to {dest1}")
    
    # Programmatic verification
    with pdfplumber.open(dest1) as pdf:
        text1 = pdf.pages[0].extract_text()
        
    print("\n--- Extracted Text from Test 1 PDF ---")
    print(text1)
    print("---------------------------------------")
    
    found_t1 = "VERIFY-FIX-TEST-12345" in text1
    orig_gone_t1 = "Sample" not in text1
    
    print(f"New text 'VERIFY-FIX-TEST-12345' found: {found_t1}")
    print(f"Original text 'Sample' gone: {orig_gone_t1}")
    
    # -------------------------------------------------------------
    # TEST 2: Replaces 'PDF' with 'VERIFY-FIX-TEST-67890'
    # 'PDF' is at x=147.0, y=76.74, w=36.0, h=24.8
    # Ratios: x=0.247, y=0.091, w=0.060, h=0.029
    # -------------------------------------------------------------
    print("\n--- Running Test 2 ---")
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
    
    files = {"file": open(src_pdf, "rb")}
    data = {"edits": json.dumps(edits2)}
    
    r2 = requests.post(f"{BASE}/edit/edit-pdf-text", headers=headers, files=files, data=data)
    files["file"].close()
    
    print(f"Response ({r2.status_code}): {r2.text}")
    if r2.status_code != 200:
        print("Test 2 failed to process edit.")
        return
        
    dl_url2 = r2.json()["download_url"]
    dl_res2 = requests.get(f"{BASE}{dl_url2}")
    dest2 = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\downloaded_verify_2.pdf"
    with open(dest2, "wb") as f:
        f.write(dl_res2.content)
    print(f"Downloaded Test 2 result to {dest2}")
    
    # Programmatic verification
    with pdfplumber.open(dest2) as pdf:
        text2 = pdf.pages[0].extract_text()
        
    print("\n--- Extracted Text from Test 2 PDF ---")
    print(text2)
    print("---------------------------------------")
    
    found_t2 = "VERIFY-FIX-TEST-67890" in text2
    orig_gone_t2 = "PDF" not in text2
    
    print(f"New text 'VERIFY-FIX-TEST-67890' found: {found_t2}")
    print(f"Original text 'PDF' gone: {orig_gone_t2}")
    
    print("\n=== VERIFICATION VERDICT ===")
    if found_t1 and orig_gone_t1 and found_t2 and orig_gone_t2:
        print("VERDICT: CONFIRMED FIXED")
    else:
        print("VERDICT: STILL BROKEN")

if __name__ == "__main__":
    run_verification()
