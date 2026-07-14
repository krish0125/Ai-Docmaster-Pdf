import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

key = os.getenv('GROK_API_KEY', '')
print(f"Loaded key: {key[:10]}...{key[-5:] if len(key) > 5 else ''} (length: {len(key)})")

if not key:
    print("No key found!")
    exit(1)

client = openai.OpenAI(api_key=key, base_url="https://api.x.ai/v1")

import urllib.request
import json

url = "https://api.x.ai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}
data = {
    "model": "grok-2-1212",
    "messages": [{"role": "user", "content": "say test"}]
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode('utf-8'),
    headers=headers,
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        print("SUCCESS! Raw Response:")
        print(html)
except Exception as e:
    print("FAILED with Exception:")
    if hasattr(e, 'read'):
        print(e.code, e.read().decode('utf-8'))
    else:
        print(str(e))
