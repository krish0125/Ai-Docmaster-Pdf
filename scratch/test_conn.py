import requests

try:
    res = requests.get("http://127.0.0.1:5500/", timeout=5)
    print("Status Code:", res.status_code)
    print("Content length:", len(res.content))
except Exception as e:
    print("Error:", e)
