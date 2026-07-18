import urllib.request
import urllib.parse
import json
import uuid
import os

API_BASE = 'http://127.0.0.1:5001'

def create_dummy_pdf(filename):
    # Minimal 1-page PDF structure
    with open(filename, 'wb') as f:
        f.write(b'%PDF-1.4\n'
                b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
                b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
                b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << >> /Contents 4 0 R >>\nendobj\n'
                b'4 0 obj\n<< /Length 40 >>\nstream\nBT /F1 12 Tf 72 712 Td (Dummy PDF File) Tj ET\nendstream\nendobj\n'
                b'xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000111 00000 n\n0000000212 00000 n\n'
                b'trailer\n<< /Size 5 /Root 1 0 R >>\n'
                b'startxref\n303\n%%EOF\n')

def post_json(url, data, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:
            return e.code, {'error': e.reason}
    except Exception as e:
        return 0, {'error': str(e)}

def post_multipart(url, files, fields, token=None):
    boundary = uuid.uuid4().hex
    headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    body = bytearray()
    for name, value in fields.items():
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode('utf-8'))
        body.extend(f'{value}\r\n'.encode('utf-8'))
        
    for name, filename, content_type, data in files:
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {content_type}\r\n\r\n'.encode('utf-8'))
        body.extend(data)
        body.extend(b'\r\n')
        
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:
            return e.code, {'error': e.reason}
    except Exception as e:
        return 0, {'error': str(e)}

def test_all():
    print("Creating dummy files...")
    create_dummy_pdf("dummy1.pdf")
    create_dummy_pdf("dummy2.pdf")
    
    # 1. Sign up
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    signup_data = {
        "name": "Test User",
        "email": email,
        "password": "password123"
    }
    status, res = post_json(f"{API_BASE}/auth/signup", signup_data)
    print(f"Signup: HTTP {status}, response: {res}")
    if status != 201:
        print("Signup failed. Exiting.")
        return
        
    # 2. Login
    login_data = {
        "email": email,
        "password": "password123"
    }
    status, res = post_json(f"{API_BASE}/auth/login", login_data)
    print(f"Login: HTTP {status}")
    token = res.get('token')
    if not token:
        print("Login failed. Exiting.")
        return

    results = []

    # 1. Edit PDF Text
    print("\nTesting Edit PDF Text...")
    with open("dummy1.pdf", "rb") as f:
        pdf_data = f.read()
    status, res = post_multipart(
        f"{API_BASE}/edit/edit-pdf-text",
        files=[("file", "dummy1.pdf", "application/pdf", pdf_data)],
        fields={"edits": "[]"},
        token=token
    )
    print(f"Edit PDF Text: HTTP {status}, response: {res}")
    results.append(("Edit PDF Text", "Edit", "Pass" if status == 200 else f"Fail ({status}: {res.get('error')})"))

    # 2. Barcode Generator
    print("\nTesting Barcode Generator...")
    status, res = post_json(
        f"{API_BASE}/utils/barcode",
        {"data": "12345678", "type": "code128"},
        token=token
    )
    print(f"Barcode: HTTP {status}, response: {res}")
    results.append(("Barcode Generator", "Utility", "Pass" if status == 200 else f"Fail ({status}: {res.get('error')})"))

    # 3. Merge PDF
    print("\nTesting Merge PDF...")
    with open("dummy1.pdf", "rb") as f1, open("dummy2.pdf", "rb") as f2:
        pdf1_data = f1.read()
        pdf2_data = f2.read()
    status, res = post_multipart(
        f"{API_BASE}/pdf/merge",
        files=[
            ("files", "dummy1.pdf", "application/pdf", pdf1_data),
            ("files", "dummy2.pdf", "application/pdf", pdf2_data)
        ],
        fields={},
        token=token
    )
    print(f"Merge PDF: HTTP {status}, response: {res}")
    results.append(("Merge PDF", "Organize/Merge/Split", "Pass" if status == 200 else f"Fail ({status}: {res.get('error')})"))

    # 4. Split PDF
    print("\nTesting Split PDF...")
    status, res = post_multipart(
        f"{API_BASE}/pdf/split",
        files=[("file", "dummy1.pdf", "application/pdf", pdf_data)],
        fields={"pages": "1"},
        token=token
    )
    print(f"Split PDF: HTTP {status}, response: {res}")
    results.append(("Split PDF", "Organize/Merge/Split", "Pass" if status == 200 else f"Fail ({status}: {res.get('error')})"))

    # 5. QR Code Generator
    print("\nTesting QR Code...")
    status, res = post_json(
        f"{API_BASE}/utils/qr",
        {"data": "https://example.com"},
        token=token
    )
    print(f"QR Code: HTTP {status}, response: {res}")
    results.append(("QR Code Generator", "Utility", "Pass" if status == 200 else f"Fail ({status}: {res.get('error')})"))

    # 6. AI Summarizer
    print("\nTesting AI Summarizer...")
    status, res = post_multipart(
        f"{API_BASE}/ai/summary",
        files=[("file", "dummy1.pdf", "application/pdf", pdf_data)],
        fields={"mode": "brief"},
        token=token
    )
    print(f"AI Summarizer: HTTP {status}, response: {res}")
    results.append(("AI Summarizer", "AI", "Pass" if status == 200 else f"Fail ({status}: {res.get('error')})"))

    # Cleanup local dummy files
    try:
        os.remove("dummy1.pdf")
        os.remove("dummy2.pdf")
    except Exception:
        pass

    print("\n" + "="*50)
    print(f"{'Tool':<25} | {'Section':<20} | {'Status'}")
    print("-"*60)
    for tool, sec, stat in results:
        print(f"{tool:<25} | {sec:<20} | {stat}")
    print("="*50)

if __name__ == "__main__":
    test_all()
