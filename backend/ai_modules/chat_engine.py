"""Chat-with-PDF engine — powered by Google Gemini (google-genai SDK).

Uses the NEW ``google-genai`` SDK (``from google import genai``), **not** the
deprecated ``google-generativeai`` package.
"""

from config import Config

# ---------------------------------------------------------------------------
# Client singleton
# ---------------------------------------------------------------------------
_client = None
_GENAI_AVAILABLE = False

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    print("[ChatEngine] google-genai is not installed")
    genai = None  # type: ignore[assignment]


def get_client():
    """Create / return a cached ``genai.Client``."""
    global _client
    if not _GENAI_AVAILABLE:
        return None
    if not Config.GEMINI_API_KEY:
        return None
    if _client is None:
        _client = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate_context(text: str, max_chars: int = 35000) -> str:
    """Keep the first ~30 000 chars and last ~5 000 chars of *text* to stay
    within typical context-window limits while preserving key information
    from both the start and end of the document.
    """
    if len(text) <= max_chars:
        return text
    head = 30000
    tail = 5000
    return (
        text[:head]
        + '\n\n[... content truncated for length ...]\n\n'
        + text[-tail:]
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_response(context: str, question: str) -> str:
    """Low-level Gemini API call.

    Builds a prompt from *context* + *question*, sends it to
    ``gemini-2.0-flash``, and returns the model's text response.
    """
    client = get_client()
    if client is None:
        if not _GENAI_AVAILABLE:
            return (
                'The google-genai package is not installed. '
                'Please run: pip install google-genai'
            )
        if not Config.GEMINI_API_KEY:
            return (
                'Gemini API key is not configured. '
                'Please set GEMINI_API_KEY in your .env file. '
                'You can get one at https://aistudio.google.com/app/apikey'
            )
        return 'Could not initialise Gemini client.'

    prompt = (
        "You are a helpful AI assistant specializing in document analysis. "
        "Answer the user's question based on the provided document context. "
        "If the answer is not in the context, say so clearly.\n\n"
        f"--- DOCUMENT CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
        f"User Question: {question}\n\n"
        "Please provide a clear, accurate, and helpful answer:"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f'Error communicating with Gemini: {str(e)}'


def chat_with_pdf(pdf_text: str, question: str, chat_history: list | None = None) -> str:
    """Send a question about a PDF document to Gemini and return the answer.

    *chat_history* is an optional list of ``{"role": "user"|"assistant", "content": "..."}``
    dicts used to maintain conversational context.
    """
    truncated = _truncate_context(pdf_text)

    # Build conversational context from history
    history_context = ''
    if chat_history:
        recent = chat_history[-10:]  # keep last 10 exchanges
        for msg in recent:
            role = 'User' if msg.get('role') == 'user' else 'Assistant'
            history_context += f"{role}: {msg.get('content', '')}\n"
        history_context = (
            "\n--- PREVIOUS CONVERSATION ---\n"
            + history_context
            + "--- END CONVERSATION ---\n"
        )

    full_context = truncated + history_context
    return generate_response(full_context, question)
