import os
import urllib.request
import json

# We need to register a user, log in, and call the /ai/summary endpoint.
BASE_URL = "http://127.0.0.1:5001"

# 1. Signup / Register
signup_data = {
    "name": "Test User",
    "email": "test_ai_user@example.com",
    "password": "Password123"
}
req = urllib.request.Request(
    f"{BASE_URL}/auth/signup",
    data=json.dumps(signup_data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req) as res:
        print("Signup success:", res.read().decode())
except Exception as e:
    if hasattr(e, 'read'):
        print("Signup exception:", e.code, e.read().decode())
    else:
        print("Signup exception:", str(e))

# 2. Login
login_data = {
    "email": "test_ai_user@example.com",
    "password": "Password123"
}
req = urllib.request.Request(
    f"{BASE_URL}/auth/login",
    data=json.dumps(login_data).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
token = None
try:
    with urllib.request.urlopen(req) as res:
        body = json.loads(res.read().decode())
        token = body.get("token")
        print("Login success. Token obtained.")
except Exception as e:
    if hasattr(e, 'read'):
        print("Login exception:", e.code, e.read().decode())
    else:
        print("Login exception:", str(e))
    exit(1)

# 3. Call summary with X-Grok-Key
boundary = b"----WebKitFormBoundary7MA4YWxkTrZu0gW"
body = (
    b"--" + boundary + b"\r\n" +
    b'Content-Disposition: form-data; name="mode"\r\n\r\nbrief\r\n' +
    b"--" + boundary + b"\r\n" +
    b'Content-Disposition: form-data; name="file"; filename="dummy.pdf"\r\n' +
    b'Content-Type: application/pdf\r\n\r\n'
)
with open("dummy.pdf", "rb") as f:
    pdf_bytes = f.read()
body += pdf_bytes + b"\r\n--" + boundary + b"--\r\n"

# Load test Grok key from environment variable (never hardcode secrets)
test_grok_key = os.environ.get("TEST_GROK_KEY", "")
if not test_grok_key:
    print("WARNING: TEST_GROK_KEY environment variable not set. X-Grok-Key header will be empty.")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW",
    # Custom Grok key loaded from environment (set TEST_GROK_KEY before running)
    "X-Grok-Key": test_grok_key
}

req = urllib.request.Request(
    f"{BASE_URL}/ai/summary",
    data=body,
    headers=headers,
    method="POST"
)

try:
    with urllib.request.urlopen(req) as res:
        print("Summary success:", res.read().decode())
except Exception as e:
    if hasattr(e, 'read'):
        print("Summary exception (this is expected!):")
        print("HTTP Status Code:", e.code)
        print("Response Body:", e.read().decode())
    else:
        print("Summary exception:", str(e))
