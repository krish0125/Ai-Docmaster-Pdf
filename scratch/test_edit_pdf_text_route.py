import os
import requests
import json
import pdfplumber

def test_route():
    BASE = "http://localhost:5001"
    
    # 1. Login/Signup to get token
    test_email = "audit_user@test.com"
    test_pass = "auditpass123"
    token = ""
    try:
        r = requests.post(f"{BASE}/auth/login", json={"email": test_email, "password": test_pass})
        if r.status_code == 200:
            token = r.json()['token']
        else:
            requests.post(f"{BASE}/auth/signup", json={"name": "Audit User", "email": test_email, "password": test_pass})
            r = requests.post(f"{BASE}/auth/login", json={"email": test_email, "password": test_pass})
            token = r.json()['token']
    except Exception as e:
        print(f"Auth failed: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Upload file with edits
    fixture_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend\tests\fixtures"
    filename = "sample_1page.pdf"
    fpath = os.path.join(fixture_dir, filename)
    
    # Let's define the edits.
    # In sample_1page.pdf, the first word is "Sample" at approx coordinates x=78, y=76.7
    # Page dimensions: width=595.275, height=841.889
    # Ratio: x = 78/595.275 = 0.131, y = 76.7/841.889 = 0.091
    # Width ratio: 64/595.275 = 0.107, Height ratio: 24/841.889 = 0.028
    edits = [
        {
            "id": "text-node-0",
            "page_index": 0,
            "type": "edit",
            "x": 0.131,
            "y": 0.091,
            "width": 0.107,
            "height": 0.028,
            "text": "PRACTICAL-2-EDITED-TEST",
            "font_family": "Helvetica",
            "font_size": 12,
            "color": "#000000",
            "bold": False,
            "italic": False,
            "align": "left"
        }
    ]
    
    files = {"file": open(fpath, "rb")}
    data = {"edits": json.dumps(edits)}
    
    print("Sending /edit/edit-pdf-text request...")
    r = requests.post(f"{BASE}/edit/edit-pdf-text", headers=headers, files=files, data=data)
    files["file"].close()
    
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}")
    
    if r.status_code == 200:
        res = r.json()
        download_url = res["download_url"]
        print(f"Download URL: {download_url}")
        
        # Download the file
        dl_res = requests.get(f"{BASE}{download_url}")
        out_path = r"c:\Users\kishu\Desktop\Ai Docmaster\scratch\downloaded_output.pdf"
        with open(out_path, "wb") as f:
            f.write(dl_res.content)
        print(f"Downloaded to {out_path}")
        
        # Extract text via pdfplumber
        with pdfplumber.open(out_path) as pdf:
            txt = pdf.pages[0].extract_text()
            print("--- EXTRACTED TEXT ---")
            print(txt)
            print("----------------------")
            if "PRACTICAL-2-EDITED-TEST" in txt:
                print("SUCCESS: New text found!")
            else:
                print("FAILURE: New text NOT found!")

if __name__ == "__main__":
    test_route()
