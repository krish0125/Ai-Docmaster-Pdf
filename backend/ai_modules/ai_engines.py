"""AI Engines — Phase 6: Writing, QA, Quiz, Business, Student tools.

All functions use the existing get_client() + call_gemini_with_retry pattern
from chat_engine.py. JSON structured output is parsed with a safe fallback.
"""

from __future__ import annotations
import json, re


def _client():
    from ai_modules.chat_engine import get_client
    return get_client()


def _ask(prompt: str, max_tokens: int = 8192) -> str:
    """Send a single-turn prompt to Gemini and return the text response."""
    from ai_modules.exceptions import call_gemini_with_retry, parse_gemini_error
    client = _client()
    if client is None:
        from ai_modules.exceptions import GeminiAPIError
        raise GeminiAPIError("Gemini API client not initialized. Configure GEMINI_API_KEY in .env.", status_code=503)

    try:
        response = call_gemini_with_retry(
            client=client,
            model='gemini-2.5-flash',
            contents=[{'parts': [{'text': prompt}]}],
            config={'max_output_tokens': max_tokens}
        )
        return (response.text or '').strip()
    except Exception as e:
        from ai_modules.exceptions import GeminiAPIError
        if isinstance(e, GeminiAPIError):
            raise e
        raise parse_gemini_error(e, model_name='gemini-2.5-flash')



def _parse_json(text: str) -> dict | list:
    """Extract and parse the first JSON object/array from *text*."""
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try extracting from markdown code block
    m = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # Fallback: return raw text as a dict
    return {'raw': text}


# ─────────────────────────────────────────────────────────────────────────────
# QA / Explanation
# ─────────────────────────────────────────────────────────────────────────────

def explain_pdf(text: str) -> str:
    """Return a plain-language explanation of the document's main topic."""
    return _ask(
        f"Explain the following document to a non-expert in 3-5 clear paragraphs.\n\n{text[:8000]}"
    )


def answer_question(text: str, question: str) -> str:
    """Answer a specific question based on the PDF content."""
    return _ask(
        f"Document content:\n{text[:7000]}\n\nQuestion: {question}\n\n"
        "Answer clearly and concisely based only on the document."
    )


def extract_keywords(text: str) -> list[dict]:
    """Extract key terms and their definitions from the document."""
    raw = _ask(
        f"Extract the 15 most important keywords/terms from this document.\n"
        f"Return ONLY a JSON array where each item has 'term' and 'definition'.\n\n{text[:7000]}"
    )
    result = _parse_json(raw)
    if isinstance(result, list):
        return result
    return [{'term': 'Extraction failed', 'definition': str(result)}]


# ─────────────────────────────────────────────────────────────────────────────
# Quiz / MCQ
# ─────────────────────────────────────────────────────────────────────────────

def generate_quiz(text: str, count: int = 10) -> list[dict]:
    """Generate a true/false quiz from the document."""
    raw = _ask(
        f"Create {count} true/false quiz questions from this document.\n"
        "Return ONLY a JSON array. Each item: {\"question\": \"...\", \"answer\": true/false, \"explanation\": \"...\"}.\n\n"
        f"{text[:7000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, list) else [{'error': str(result)}]


def generate_mcq(text: str, count: int = 10) -> list[dict]:
    """Generate multiple-choice questions from the document."""
    raw = _ask(
        f"Create {count} multiple-choice questions from this document.\n"
        "Return ONLY a JSON array. Each item: "
        "{\"question\": \"...\", \"options\": [\"A)...\",\"B)...\",\"C)...\",\"D)...\"], "
        "\"correct\": \"A\", \"explanation\": \"...\"}.\n\n"
        f"{text[:7000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, list) else [{'error': str(result)}]


# ─────────────────────────────────────────────────────────────────────────────
# Writing Tools
# ─────────────────────────────────────────────────────────────────────────────

def check_grammar(text: str) -> dict:
    """Check grammar and return corrected text with a list of issues."""
    raw = _ask(
        "Check the grammar and spelling in the following text.\n"
        "Return ONLY JSON: {\"corrected\": \"...\", \"issues\": [{\"original\": \"...\", \"suggestion\": \"...\"}]}.\n\n"
        f"{text[:6000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'corrected': text, 'issues': []}


def improve_writing(text: str) -> str:
    """Return an improved, more professional version of the text."""
    return _ask(
        f"Rewrite the following text to be clearer, more professional and engaging. "
        f"Preserve all the original meaning.\n\n{text[:6000]}"
    )


def translate_text(text: str, target_lang: str) -> str:
    """Translate text into *target_lang*."""
    return _ask(f"Translate the following text into {target_lang}. Return only the translation.\n\n{text[:6000]}")


def rewrite_text(text: str, style: str) -> str:
    """Rewrite text in a different style (formal, casual, academic, etc.)."""
    return _ask(f"Rewrite the following text in a {style} style.\n\n{text[:6000]}")


def change_tone(text: str, tone: str) -> str:
    """Change the tone of the text (professional, friendly, assertive, empathetic)."""
    return _ask(f"Rewrite the following text with a {tone} tone. Keep all the facts.\n\n{text[:6000]}")


def proofread(text: str) -> dict:
    """Proofread and return corrections."""
    raw = _ask(
        "Proofread the following text and list all corrections.\n"
        "Return ONLY JSON: {\"proofread_text\": \"...\", \"corrections\": [\"description of each fix\"]}.\n\n"
        f"{text[:6000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'proofread_text': text, 'corrections': []}


# ─────────────────────────────────────────────────────────────────────────────
# Business Tools
# ─────────────────────────────────────────────────────────────────────────────

def analyze_contract(text: str) -> dict:
    """Identify key clauses, risks, and obligations in a contract."""
    raw = _ask(
        "Analyze this contract document and extract:\n"
        "Return ONLY JSON: {\"parties\": [], \"key_clauses\": [], \"obligations\": [], "
        "\"risks\": [], \"termination\": \"\", \"summary\": \"\"}.\n\n"
        f"{text[:8000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'summary': str(result)}


def read_invoice(text: str) -> dict:
    """Extract structured invoice data from text."""
    raw = _ask(
        "Extract all data from this invoice. "
        "Return ONLY JSON: {\"vendor\": \"\", \"invoice_number\": \"\", \"date\": \"\", "
        "\"due_date\": \"\", \"line_items\": [], \"subtotal\": \"\", \"tax\": \"\", \"total\": \"\"}.\n\n"
        f"{text[:6000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'raw': str(result)}


def analyze_financial(text: str) -> dict:
    """Summarise key financial metrics from a report."""
    raw = _ask(
        "Analyze this financial document. "
        "Return ONLY JSON: {\"key_metrics\": {}, \"trends\": [], \"risks\": [], "
        "\"opportunities\": [], \"summary\": \"\"}.\n\n"
        f"{text[:8000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'summary': str(result)}


def review_legal(text: str) -> dict:
    """High-level legal document review (not legal advice)."""
    raw = _ask(
        "Review this legal document (NOT legal advice — for informational purposes only).\n"
        "Return ONLY JSON: {\"document_type\": \"\", \"key_points\": [], "
        "\"potential_issues\": [], \"summary\": \"\", \"disclaimer\": \"This is not legal advice.\"}.\n\n"
        f"{text[:8000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'summary': str(result)}


# ─────────────────────────────────────────────────────────────────────────────
# Student Tools
# ─────────────────────────────────────────────────────────────────────────────

def assignment_helper(text: str, task: str) -> str:
    """Help with an assignment task based on document content."""
    return _ask(
        f"Based on the following document, help with this task: {task}\n\n"
        f"Document:\n{text[:6000]}"
    )


def research_assistant(text: str, topic: str = '') -> dict:
    """Generate a research outline and key points from the document."""
    prompt = (
        f"Based on this document{', focusing on: ' + topic if topic else ''}, "
        "create a structured research summary.\n"
        "Return ONLY JSON: {\"title\": \"\", \"thesis\": \"\", \"main_points\": [], "
        "\"supporting_evidence\": [], \"conclusions\": [], \"further_reading\": []}.\n\n"
        f"{text[:7000]}"
    )
    raw = _ask(prompt)
    result = _parse_json(raw)
    return result if isinstance(result, dict) else {'summary': str(result)}


def cite_sources(text: str, style: str = 'APA') -> list[str]:
    """Generate citations from references found in the document."""
    raw = _ask(
        f"Find all references/sources in this document and format them as {style} citations.\n"
        "Return ONLY a JSON array of citation strings.\n\n"
        f"{text[:6000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, list) else [str(result)]


def generate_cover_letter(resume_text: str, job_description: str) -> str:
    """Generate a cover letter from resume content and job description."""
    return _ask(
        f"Write a professional cover letter based on this resume for the following job.\n\n"
        f"Resume:\n{resume_text[:3000]}\n\nJob Description:\n{job_description[:2000]}"
    )


def generate_interview_questions(resume_text: str) -> list[str]:
    """Generate likely interview questions based on a resume."""
    raw = _ask(
        "Generate 15 likely interview questions for a candidate with this resume.\n"
        "Return ONLY a JSON array of question strings.\n\n"
        f"{resume_text[:4000]}"
    )
    result = _parse_json(raw)
    return result if isinstance(result, list) else [str(result)]
