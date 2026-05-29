"""
Gemini API Key Verification Script
Tests if your GEMINI_API_KEY is valid and working with gemini-2.5-flash.
"""

import os
import sys

# Fix Windows console encoding for emoji/unicode
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Load .env file ──
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[OK] Loaded .env file")
except ImportError:
    print("[WARN] python-dotenv not installed - reading from system environment only")

# ── Check API Key ──
api_key = os.getenv("GEMINI_API_KEY", "").strip()

if not api_key:
    print("\n[FAIL] GEMINI_API_KEY is missing or blank!")
    print("   -> Make sure it's set in your .env file or system environment variables.")
    print("   -> Get a key from: https://aistudio.google.com/apikey")
    sys.exit(1)

print(f"[OK] API Key found: {api_key[:10]}...{api_key[-4:]}  (length: {len(api_key)})")

# ── Test Gemini API ──
print("\n[...] Sending test request to Gemini (gemini-2.5-flash)...\n")

try:
    from google import genai

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Say exactly: Hello World! I am Gemini and I am working correctly.",
    )

    reply = response.text.strip()
    print(f"=== GEMINI API KEY IS WORKING PERFECTLY! ===")
    print(f"Response: {reply}")
    print(f"=============================================")

except ImportError:
    print("[FAIL] google-genai SDK is not installed!")
    print("   -> Run: pip install google-genai")
    sys.exit(1)

except Exception as e:
    error_msg = str(e)

    if "API_KEY_INVALID" in error_msg or "401" in error_msg:
        print("[FAIL] Invalid API Key! The key was rejected by Google.")
        print("   -> Double-check your key at: https://aistudio.google.com/apikey")
    elif "403" in error_msg:
        print("[FAIL] API Key doesn't have permission to use Gemini.")
        print("   -> Make sure the Generative Language API is enabled in your Google Cloud project.")
    elif "429" in error_msg:
        print("[FAIL] Rate limit exceeded! Too many requests.")
        print("   -> Wait a minute and try again.")
    elif "timeout" in error_msg.lower() or "connect" in error_msg.lower():
        print("[FAIL] Network error - could not reach Google's servers.")
        print("   -> Check your internet connection and try again.")
    else:
        print(f"[FAIL] Gemini API call failed!")

    print(f"\n   Error details: {error_msg}")
    sys.exit(1)
