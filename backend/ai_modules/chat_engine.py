"""Chat-with-PDF engine — powered by Google Gemini (google-genai SDK).

Uses the NEW ``google-genai`` SDK (``from google import genai``), **not** the
deprecated ``google-generativeai`` package.
"""

import re
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
    """Create / return a cached or request-specific ``genai.Client``."""
    global _client
    if not _GENAI_AVAILABLE:
        return None

    # Dynamically extract client API key from Flask request headers if available
    key = None
    try:
        from flask import has_request_context, request
        if has_request_context():
            key = request.headers.get('X-Gemini-Key')
    except Exception:
        pass

    if not key:
        key = Config.GEMINI_API_KEY

    if not key:
        return None

    # If it is a request-specific key, return a fresh client instance to prevent caching issues
    if key != Config.GEMINI_API_KEY:
        return genai.Client(api_key=key)

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


def _get_keyword_fallback_answer(context: str, question: str) -> str:
    """Smart keyword-matching excerpt search over the document context when Gemini fails."""
    # Extract terms (3+ chars) from the question to search for matching sentences
    q_words = [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', question) if w.lower() not in {
        'what', 'when', 'where', 'who', 'how', 'why', 'this', 'that', 'with', 'from', 'about', 'document', 'pdfs', 'pdf', 'find'
    }]
    
    # Split the document text into sentences
    sentences = re.split(r'(?<=[.!?])\s+', context)
    scored_sentences = []
    
    for sent in sentences:
        sent_clean = sent.strip()
        if not sent_clean or len(sent_clean) < 15:
            continue
        # Score based on keyword matches
        score = sum(1 for w in q_words if w in sent_clean.lower())
        if score > 0:
            scored_sentences.append((score, sent_clean))
            
    # Sort matching sentences by matching score in descending order
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    best_matches = [s[1] for s in scored_sentences[:3]]
    
    if best_matches:
        excerpt = "\n\n".join(f"• ... {m} ..." for m in best_matches)
        return (
            "⚠️ **Gemini AI Quota Exceeded (429 Rate Limit)**\n\n"
            "Your default API key has reached its request limit. To enjoy seamless, high-speed, and premium AI insights, "
            "please configure your own free Gemini API key in the **User Profile dropdown (top-right) → API Configuration**.\n\n"
            "🔍 **Document Excerpt Fallback Search:**\n"
            f"Here are matching segments found in your document:\n\n{excerpt}"
        )
    else:
        return (
            "⚠️ **Gemini AI Quota Exceeded (429 Rate Limit)**\n\n"
            "Your default API key has reached its request limit. To enjoy seamless, high-speed, and premium AI insights, "
            "please configure your own free Gemini API key in the **User Profile dropdown (top-right) → API Configuration**.\n\n"
            "I scanned the document but could not find a direct sentence match for your specific question. Please try rephrasing or configure your API key."
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
        return _get_keyword_fallback_answer(context, question)

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
        err_msg = str(e)
        print(f"[ChatEngine] Gemini error: {err_msg}. Triggering smart fallback...")
        return _get_keyword_fallback_answer(context, question)


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
