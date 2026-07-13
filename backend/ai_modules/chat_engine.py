"""Chat with PDF engine — powered by xAI Grok (openai SDK)."""

from config import Config

_client = None
_OPENAI_AVAILABLE = False

try:
    import openai
    _OPENAI_AVAILABLE = True
except ImportError:
    openai = None

def get_client():
    global _client
    if _client is not None:
        return _client
    if not _OPENAI_AVAILABLE:
        return None
    from flask import request
    try:
        if request:
            key = request.headers.get('X-Grok-Key') or request.headers.get('X-Gemini-Key')
            if key and key.strip():
                return openai.OpenAI(api_key=key.strip(), base_url="https://api.x.ai/v1")
    except RuntimeError:
        pass
    if Config.GROK_API_KEY:
        _client = openai.OpenAI(api_key=Config.GROK_API_KEY, base_url="https://api.x.ai/v1")
        return _client
    return None

def build_chat_prompt(pdf_text: str, user_question: str) -> str:
    return f"""You are a helpful AI assistant. Answer the user's question based strictly on the provided PDF document.

--- DOCUMENT START ---
{pdf_text[:30000]}
--- DOCUMENT END ---

If the answer is not contained in the document, state that clearly rather than making up information.
Question: {user_question}
"""

def chat_with_pdf(pdf_text: str, user_question: str, chat_history: list = None) -> str:
    if not pdf_text.strip():
        return "I cannot answer because no text could be extracted from the PDF."
    if not user_question.strip():
        return "Please provide a question."

    from ai_modules.exceptions import GrokAPIError, call_grok_with_retry

    client = get_client()
    if client is None:
        raise GrokAPIError("Grok API client could not be initialized.", "invalid_key", 401)

    system_msg = "You are a helpful AI assistant. Answer the user's question based strictly on the provided PDF document."
    messages = [{"role": "system", "content": system_msg}]
    
    if chat_history:
        for msg in chat_history:
            role = 'assistant' if msg['role'] == 'model' else msg['role']
            messages.append({"role": role, "content": msg['content']})

    context_prompt = f"--- DOCUMENT START ---\n{pdf_text[:30000]}\n--- DOCUMENT END ---\nQuestion: {user_question}"
    messages.append({"role": "user", "content": context_prompt})

    response = call_grok_with_retry(
        client=client,
        model='grok-2-latest',
        messages=messages
    )
    return response.choices[0].message.content.strip()
