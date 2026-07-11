import os
import requests
import json
import pdfplumber
import random

def test_perfect_fit():
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
    # Replaces 'Sample' (6 chars) with 'Change' (6 chars)
    # Ratios: x=0.131, y=0.091, w=0.107, h=0.029
    # -------------------------------------------------------------
    edits = [
        {
            "id": "text-node-0",
            "page_index": 0,
            "type": "edit",
            "x": 0.131,
            "y": 0.091,
            "width": 0.107,
            "height": 0.029,
            "text": "Change",
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
        dest = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\downloaded_perfect_fit.pdf"
        with open(dest, "wb") as f:
            f.write(dl_res.content)
            
        with pdfplumber.open(dest) as pdf:
            text = pdf.pages[0].extract_text()
            
        print("--- EXTRACTED FIRST LINE ---")
        print(text.split("\n")[0])
        print("----------------------------")
        
        if "Change PDF Page 1" in text:
            print("SUCCESS: Text edited and extracted cleanly without interleaving!")
        else:
            print("FAILURE: Text layer is still jumbled/incorrect.")
            
if __name__ == "__main__":
    test_perfect_fit()
