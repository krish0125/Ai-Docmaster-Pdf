"""Phase 6 AI Modules — writing, quiz, translation, business (Powered by Google Gemini)."""

from ai_modules.chat_engine import get_client, MODEL
from ai_modules.exceptions import GeminiAPIError, call_gemini_with_retry

def _ask(prompt: str, as_json: bool = False, model: str = None):
    if model is None:
        model = MODEL
    client = get_client()
    if not client:
        raise GeminiAPIError("Gemini API client not initialized. Check GEMINI_API_KEY.", "invalid_key", 401)

    contents = [{"role": "user", "parts": [{"text": prompt}]}]

    kwargs = {}
    if as_json:
        # google-genai 2.6.0 JSON mode: pass via GenerateContentConfig
        from google.genai import types as genai_types
        kwargs['config'] = genai_types.GenerateContentConfig(
            response_mime_type="application/json"
        )

    response = call_gemini_with_retry(client=client, model=model, contents=contents, **kwargs)
    return response.text.strip()

def explain_pdf(text: str) -> dict:
    prompt = f"Explain this text like I am 5 years old.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'explanation': res, 'word_count': len(res.split())}

def answer_question(text: str, question: str) -> dict:
    prompt = f"Based ONLY on the text below, answer this question: {question}\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'answer': res, 'word_count': len(res.split())}

def extract_keywords(text: str) -> dict:
    prompt = f"Extract the top 10 keywords or phrases from this text. Return as comma separated values.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    kws = [k.strip() for k in res.split(',')]
    return {'keywords': kws, 'count': len(kws)}

def generate_quiz(text: str, count: int = 5) -> dict:
    prompt = (
        f"Generate {count} short-answer quiz questions and their answers from this text. "
        "Return ONLY a valid JSON object with a key 'questions' containing an array of objects "
        f"with 'question' and 'answer' keys.\n\nTEXT:\n{text[:10000]}"
    )
    import json
    res = _ask(prompt, as_json=True)
    try:
        data = json.loads(res)
        return {'quiz': data.get('questions', [])}
    except Exception:
        return {'quiz': [{'question': 'Failed to parse JSON', 'answer': res}]}

def generate_mcq(text: str, count: int = 5) -> dict:
    prompt = (
        f"Generate {count} multiple choice questions from this text. "
        "Return ONLY a valid JSON object with a key 'mcqs' containing an array of objects. "
        f"Each object must have 'question', 'options' (array of 4 strings), and 'correct_answer'.\n\nTEXT:\n{text[:10000]}"
    )
    import json
    res = _ask(prompt, as_json=True)
    try:
        data = json.loads(res)
        return {'mcqs': data.get('mcqs', [])}
    except Exception:
        return {'mcqs': []}

def check_grammar(text: str) -> dict:
    prompt = f"Check the following text for grammar, spelling, and punctuation errors. Return the corrected text only.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'corrected_text': res, 'word_count': len(res.split())}

def improve_writing(text: str) -> dict:
    prompt = f"Rewrite this text to be more engaging, clear, and professional.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'improved_text': res, 'word_count': len(res.split())}

def translate_text(text: str, target_language: str) -> dict:
    prompt = f"Translate the following text into {target_language}. Return only the translation.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'translated_text': res, 'word_count': len(res.split()), 'language': target_language}

def rewrite_text(text: str, style: str) -> dict:
    prompt = f"Rewrite the following text in a {style} style.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'rewritten_text': res, 'word_count': len(res.split()), 'style': style}

def change_tone(text: str, tone: str) -> dict:
    prompt = f"Change the tone of this text to be {tone}. Return only the text.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'toned_text': res, 'word_count': len(res.split()), 'tone': tone}

def proofread(text: str) -> dict:
    prompt = f"Proofread this text and list any errors or suggestions, followed by the corrected version.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'proofread_result': res, 'word_count': len(res.split())}

def analyze_contract(text: str) -> dict:
    prompt = f"Summarize the key terms, obligations, and potential risks in this legal contract.\n\nCONTRACT:\n{text[:15000]}"
    res = _ask(prompt)
    return {'contract_analysis': res, 'word_count': len(res.split())}

def read_invoice(text: str) -> dict:
    prompt = (
        "Extract invoice details: Invoice Number, Date, Total Amount, Vendor Name, and Line Items. "
        "Return ONLY a valid JSON object with keys: invoice_number, date, total_amount, vendor_name, line_items.\n\n"
        f"INVOICE:\n{text[:10000]}"
    )
    import json
    res = _ask(prompt, as_json=True)
    try:
        data = json.loads(res)
        return {'invoice_data': data}
    except Exception:
        return {'invoice_data': {'error': 'Parse failed', 'raw': res}}

def analyze_financial(text: str) -> dict:
    prompt = f"Analyze this financial document and provide a summary of key metrics, trends, and insights.\n\nFINANCIAL DOC:\n{text[:15000]}"
    res = _ask(prompt)
    return {'financial_analysis': res, 'word_count': len(res.split())}

def review_legal(text: str) -> dict:
    prompt = f"Review this legal document, highlighting important clauses and potential issues.\n\nDOCUMENT:\n{text[:15000]}"
    res = _ask(prompt)
    return {'legal_review': res, 'word_count': len(res.split())}

def assignment_helper(text: str, task: str) -> dict:
    prompt = f"Help me with this assignment based on the provided text. Task: {task}\n\nTEXT:\n{text[:15000]}"
    res = _ask(prompt)
    return {'assignment_help': res, 'word_count': len(res.split())}

def research_assistant(text: str, topic: str) -> dict:
    prompt = f"Act as a research assistant. Synthesize the text regarding the topic: {topic}\n\nTEXT:\n{text[:20000]}"
    res = _ask(prompt)
    return {'research_summary': res, 'word_count': len(res.split())}

def cite_sources(text: str, style: str) -> dict:
    prompt = f"Generate a bibliography or citation list in {style} format for the sources or entities mentioned in this text.\n\nTEXT:\n{text[:10000]}"
    res = _ask(prompt)
    return {'citations': res, 'word_count': len(res.split())}

def generate_cover_letter(text: str, job_description: str) -> dict:
    prompt = f"Write a professional cover letter based on this resume and the job description.\n\nJOB DESCRIPTION:\n{job_description}\n\nRESUME:\n{text[:10000]}"
    res = _ask(prompt)
    return {'cover_letter': res, 'word_count': len(res.split())}

def generate_interview_questions(text: str) -> dict:
    prompt = f"Generate 10 technical and behavioral interview questions based on the candidate's resume.\n\nRESUME:\n{text[:10000]}"
    res = _ask(prompt)
    return {'interview_questions': res, 'word_count': len(res.split())}
