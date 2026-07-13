import os

backend_dir = r"c:\Users\kishu\Desktop\Ai Docmaster\backend"

replacements = {
    'GeminiAPIError': 'GrokAPIError',
    'parse_gemini_error': 'parse_grok_error',
    'call_gemini_with_retry': 'call_grok_with_retry',
    'Gemini': 'Grok',
    'gemini_ai': 'grok_ai',
    'gemini_vision': 'grok-vision',
    'gemini-vision': 'grok-vision',
    'gemini-2.5-flash-lite': 'grok-2-latest',
    'gemini-2.5-flash': 'grok-2-latest',
    'X-Gemini-Key': 'X-Grok-Key',
    'geminiApiKeyInput': 'grokApiKeyInput',
}

for root, _, files in os.walk(backend_dir):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacements.items():
                new_content = new_content.replace(old, new)
                
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
