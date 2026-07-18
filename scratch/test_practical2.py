import os
import requests
import json
import pdfplumber
import random

def test_practical2():
    BASE = "http://localhost:5001"
    
    # Sign up/login
    rand_id = random.randint(1000, 9999)
    email = f"verify_user_{rand_id}@test.com"
    password = "Password123!"
    
    requests.post(f"{BASE}/auth/signup", json={
        "name": "Verification User",
        "email": email,
        "password": password
    })
    
    login_res = requests.post(f"{BASE}/auth/login", json={
        "email": email,
        "password": password
    })
    
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    fixture_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures"
    src_pdf = os.path.join(fixture_dir, "sample_1page.pdf")
    
    # -------------------------------------------------------------
    # Replaces entire first line (from x=78.0 to x=246.0) with 'PRACTICAL-2-EDITED-TEST'
    # Ratios: x=0.131, y=0.091, w=0.282, h=0.029
    # -------------------------------------------------------------
    edits = [
        {
            "id": "text-node-first-line",
            "page_index": 0,
            "type": "edit",
            "x": 0.131,
            "y": 0.091,
            "width": 0.282,
            "height": 0.029,
            "text": "PRACTICAL-2-EDITED-TEST",
            "font_family": "Helvetica",
            "font_size": 12,
            "color": "#000000",
            "bold": False,
            "italic": False,
            "align": "left"
        }
    ]
    
    files = {"file": open(src_pdf, "rb")}
    data = {"edits": json.dumps(edits)}
    
    r = requests.post(f"{BASE}/edit/edit-pdf-text", headers=headers, files=files, data=data)
    files["file"].close()
    
    if r.status_code == 200:
        dl_url = r.json()["download_url"]
        dl_res = requests.get(f"{BASE}{dl_url}")
        dest = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\downloaded_practical2.pdf"
        with open(dest, "wb") as f:
            f.write(dl_res.content)
            
        with pdfplumber.open(dest) as pdf:
            text = pdf.pages[0].extract_text()
            
        print("--- EXTRACTED FIRST LINE ---")
        first_line = text.split("\n")[0]
        print(first_line)
        print("----------------------------")
        
        if "PRACTICAL-2-EDITED-TEST" in first_line:
            print("SUCCESS: PRACTICAL-2-EDITED-TEST found in first line!")
        else:
            print("FAILURE: PRACTICAL-2-EDITED-TEST NOT found or jumbled!")
            
if __name__ == "__main__":
    test_practical2()
