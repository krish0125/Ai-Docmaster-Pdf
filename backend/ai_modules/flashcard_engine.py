"""AI Flashcard engine — powered by Google Gemini (google-genai SDK)."""

import re
import json
from config import Config

_client = None
_GENAI_AVAILABLE = False

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None


def get_client():
    """Create / return the unified Gemini client from chat_engine."""
    from ai_modules.chat_engine import get_client as _chat_get_client
    return _chat_get_client()


def generate_flashcards(text: str) -> list:
    """Generate a list of Q&A dicts for flashcards from a given PDF text.
    
    Returns a list of dicts: ``[{"question": "...", "answer": "..."}]``.
    """
    if not text.strip():
        return []

    client = get_client()
    if client is None:
        # Graceful fallback: local extractive Q&A generation from the text
        return _generate_fallback_flashcards(text)

    prompt = (
        "You are an educational assistant. Extract 5 to 10 high-quality question-and-answer pairs "
        "based on the following text to help students study. The questions should test understanding of "
        "key definitions, concepts, and facts. The answers should be clear, concise, and informative.\n\n"
        "--- START TEXT ---\n"
        f"{text[:15000]}\n"  # Keep within reasonable prompt size
        "--- END TEXT ---\n\n"
        "You MUST return ONLY a valid JSON array of objects, with NO additional text or markdown formatting. "
        "Each object in the array MUST have exactly these two keys: "
        "'question' and 'answer'.\n"
        "Example format:\n"
        '[\n  {"question": "What is the main topic of the text?", "answer": "The text discusses X."}\n]'
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        resp_text = response.text.strip()
        
        # Clean markdown code blocks if present
        resp_text = re.sub(r'^```(?:json)?\s*', '', resp_text, flags=re.IGNORECASE)
        resp_text = re.sub(r'\s*```$', '', resp_text)
        resp_text = resp_text.strip()

        # Robustly extract JSON array using regular expressions to strip any prefix/suffix conversational text
        json_match = re.search(r'\[\s*\{.*\}\s*\]', resp_text, re.DOTALL)
        if json_match:
            resp_text = json_match.group(0)

        cards = json.loads(resp_text)
        if isinstance(cards, list):
            # Validate format
            validated_cards = []
            for item in cards:
                if isinstance(item, dict) and 'question' in item and 'answer' in item:
                    validated_cards.append({
                        'question': str(item['question']).strip(),
                        'answer': str(item['answer']).strip()
                    })
            if validated_cards:
                return validated_cards
        
        return _generate_fallback_flashcards(text)
    except Exception as e:
        print(f"[Flashcards] Gemini failed: {e}. Using fallback...")
        return _generate_fallback_flashcards(text)


def _generate_fallback_flashcards(text: str) -> list:
    """Generate fallback flashcards by splitting sentences when Gemini is unavailable."""
    # Split text into paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 30]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split('.') if len(p.strip()) > 30]

    cards = []
    # Take up to 6 interesting sentences or paragraphs and formulate general review questions
    for i, p in enumerate(paragraphs[:6]):
        summary = p[:150] + "..." if len(p) > 150 else p
        cards.append({
            'question': f"Review Study Item {i + 1}: What is the key concept described in this section?",
            'answer': summary
        })

    # If still empty, add a placeholder
    if not cards:
        cards.append({
            'question': "No text could be processed. Please check the PDF content.",
            'answer': "Ensure your PDF has selectable text and is not a blank document or scanned image."
        })
    return cards
