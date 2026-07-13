import os
import re

backend_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content

    # 1. Generic string replacements
    replacements = {
        'GeminiAPIError': 'GrokAPIError',
        'parse_gemini_error': 'parse_grok_error',
        'call_gemini_with_retry': 'call_grok_with_retry',
        'gemini_ai': 'grok_ai',
        'gemini-vision': 'grok-vision',
        'gemini_vision': 'grok-vision',
        'X-Gemini-Key': 'X-Grok-Key',
        'GEMINI_API_KEY': 'GROK_API_KEY',
        'GEMINI': 'GROK',
        'gemini': 'grok',
        'Gemini': 'Grok',
        'grok-2.5-flash-lite': 'grok-2-latest',
        'grok-2.5-flash': 'grok-2-latest',
    }

    # Exception: we don't want to replace google-genai blindly in text, only in imports maybe,
    # but the old SDK used google.genai, we'll manually fix the big files.
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

for root, _, files in os.walk(backend_dir):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))
