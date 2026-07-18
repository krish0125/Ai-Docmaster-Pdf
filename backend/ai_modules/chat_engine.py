"""Chat with PDF engine — powered by Google Gemini (google-genai SDK)."""

from config import Config

_client = None
_GENAI_AVAILABLE = False

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None

MODEL = "gemini-2.5-flash"

def get_client():
    global _client
    if not _GENAI_AVAILABLE:
        return None
    from flask import request
    try:
        if request:
            key = request.headers.get('X-Gemini-Key')
            if key and key.strip():
                # Request-specific custom key — return a fresh client without caching globally
                return genai.Client(api_key=key.strip())
    except RuntimeError:
        pass

    # Otherwise return/cache the server-wide default client
    if _client is not None:
        return _client
    if Config.GEMINI_API_KEY:
        _client = genai.Client(api_key=Config.GEMINI_API_KEY)
        return _client
    return None


def _build_gemini_contents(pdf_text: str, user_question: str, chat_history: list = None) -> list:
    """Build a google-genai contents list from system prompt + history + latest question.

    google-genai SDK roles: 'user' and 'model' (not 'assistant').
    The system prompt and document context are prepended to the first user turn.
    """
    system_msg = (
        "You are a helpful AI assistant. Answer the user's question based strictly "
        "on the provided PDF document. If the answer is not contained in the document, "
        "state that clearly rather than making up information."
    )
    context_block = (
        f"--- DOCUMENT START ---\n{pdf_text[:30000]}\n--- DOCUMENT END ---"
    )

    contents = []

    if chat_history:
        for i, msg in enumerate(chat_history):
            role = msg.get('role', 'user')
            # Normalise 'assistant' → 'model' for google-genai SDK
            if role == 'assistant':
                role = 'model'
            content_text = msg.get('content', '')
            # Inject system context into the very first user turn
            if i == 0 and role == 'user':
                content_text = f"{system_msg}\n\n{context_block}\n\nQuestion: {content_text}"
            contents.append({"role": role, "parts": [{"text": content_text}]})

    # Append the new user question
    if not contents:
        # No history — inject system + context into this first turn
        question_text = (
            f"{system_msg}\n\n{context_block}\n\nQuestion: {user_question}"
        )
    else:
        question_text = user_question

    contents.append({"role": "user", "parts": [{"text": question_text}]})
    return contents


def chat_with_pdf(pdf_text: str, user_question: str, chat_history: list = None) -> str:
    if not pdf_text.strip():
        return "I cannot answer because no text could be extracted from the PDF."
    if not user_question.strip():
        return "Please provide a question."

    from ai_modules.exceptions import GeminiAPIError, call_gemini_with_retry

    client = get_client()
    if client is None:
        raise GeminiAPIError("Gemini API client could not be initialized.", "invalid_key", 401)

    contents = _build_gemini_contents(pdf_text, user_question, chat_history)

    response = call_gemini_with_retry(
        client=client,
        model=MODEL,
        contents=contents,
    )
    return response.text.strip()
