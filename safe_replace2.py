import os

files_to_update = [
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\ai_modules\summarizer.py",
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\ai_modules\resume_analyzer.py",
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\ai_modules\flashcard_engine.py",
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\routes\ai_routes.py",
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\routes\ocr_routes.py",
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\app.py",
    r"c:\Users\kishu\Desktop\Ai Docmaster\backend\config.py"
]

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

for filepath in files_to_update:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        for old, new in replacements.items():
            content = content.replace(old, new)
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")
