"""AI Summarizer — uses HuggingFace transformers (BART) when available,
otherwise falls back to a simple extractive approach based on word frequency.
"""

import re
from collections import Counter

# ---------------------------------------------------------------------------
# Transformer pipeline (lazy-loaded)
# ---------------------------------------------------------------------------
_summarizer = None
_TRANSFORMERS_AVAILABLE = False

try:
    from transformers import pipeline as _hf_pipeline
    _TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("[Summarizer] transformers library not installed — using extractive fallback")
    _hf_pipeline = None  # type: ignore[assignment]


def get_summarizer():
    """Lazy-load and cache the HuggingFace summarization pipeline."""
    global _summarizer
    if _summarizer is None and _TRANSFORMERS_AVAILABLE:
        try:
            _summarizer = _hf_pipeline(
                'summarization',
                model='facebook/bart-large-cnn',
                device=-1,  # CPU
            )
            print("[Summarizer] BART model loaded successfully")
        except Exception as e:
            print(f"[Summarizer] Failed to load BART model: {e}")
    return _summarizer


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_chars: int = 3000) -> list[str]:
    """Split *text* into chunks of roughly *max_chars* characters,
    splitting on sentence boundaries where possible.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: list[str] = []
    current_chunk = ''

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk += (' ' + sentence) if current_chunk else sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # If a single sentence exceeds max_chars, force-split it
            if len(sentence) > max_chars:
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
                current_chunk = ''
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)
    return chunks


# ---------------------------------------------------------------------------
# Extractive fallback (no ML required)
# ---------------------------------------------------------------------------

def _extractive_summary(text: str, num_sentences: int = 5) -> str:
    """Simple extractive summary: rank sentences by word-frequency score
    and return the top *num_sentences*.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= num_sentences:
        return text

    # Word frequency (excluding stop-words)
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at',
        'to', 'for', 'of', 'and', 'or', 'but', 'not', 'with', 'this',
        'that', 'it', 'as', 'by', 'from', 'be', 'has', 'had', 'have',
        'will', 'can', 'do', 'does', 'did', 'its', 'they', 'their', 'he',
        'she', 'we', 'you', 'i', 'my', 'your', 'our', 'his', 'her',
    }
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    word_freq = Counter(w for w in words if w not in stop_words)

    scored = []
    for idx, sent in enumerate(sentences):
        sent_words = re.findall(r'\b[a-zA-Z]+\b', sent.lower())
        score = sum(word_freq.get(w, 0) for w in sent_words)
        scored.append((score, idx, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = sorted(scored[:num_sentences], key=lambda x: x[1])  # preserve order
    return ' '.join(t[2] for t in top)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_summary(text: str, mode: str = 'brief') -> dict:
    """Generate a summary of *text*.

    Modes:
    - ``brief``  — short paragraph summary
    - ``detailed`` — longer, more comprehensive summary
    - ``bullets`` — bullet-point list
    - ``exam_notes`` — structured study notes

    Returns ``{summary, word_count, mode}``.
    """
    if not text or not text.strip():
        return {'summary': 'No text provided for summarization.', 'word_count': 0, 'mode': mode}

    clean_text = text.strip()

    if mode == 'bullets':
        return generate_bullet_points(clean_text)

    if mode == 'exam_notes':
        return generate_exam_notes(clean_text)

    summarizer = get_summarizer()

    if summarizer is not None:
        try:
            chunks = chunk_text(clean_text)
            summaries: list[str] = []

            max_len = 130 if mode == 'brief' else 300
            min_len = 30 if mode == 'brief' else 100

            for chunk in chunks:
                if len(chunk.split()) < 30:
                    summaries.append(chunk)
                    continue
                result = summarizer(
                    chunk,
                    max_length=max_len,
                    min_length=min_len,
                    do_sample=False,
                    truncation=True,
                )
                summaries.append(result[0]['summary_text'])

            combined = ' '.join(summaries)

            # For brief mode, further condense if the combined text is long
            if mode == 'brief' and len(combined.split()) > 200 and len(combined) > 500:
                result = summarizer(
                    combined[:3000],
                    max_length=150,
                    min_length=40,
                    do_sample=False,
                    truncation=True,
                )
                combined = result[0]['summary_text']

            return {
                'summary': combined,
                'word_count': len(combined.split()),
                'mode': mode,
            }
        except Exception as e:
            print(f"[Summarizer] Transformer error, falling back: {e}")

    # Fallback: extractive
    num = 3 if mode == 'brief' else 8
    summary = _extractive_summary(clean_text, num_sentences=num)
    return {
        'summary': summary,
        'word_count': len(summary.split()),
        'mode': mode,
        'method': 'extractive_fallback',
    }


def generate_bullet_points(text: str) -> dict:
    """Generate a bullet-point summary."""
    summarizer = get_summarizer()

    if summarizer is not None:
        try:
            chunks = chunk_text(text)
            all_points: list[str] = []
            for chunk in chunks:
                if len(chunk.split()) < 30:
                    all_points.append(chunk)
                    continue
                result = summarizer(
                    chunk,
                    max_length=200,
                    min_length=50,
                    do_sample=False,
                    truncation=True,
                )
                summary_text = result[0]['summary_text']
                # Split summary into individual bullet points
                sentences = re.split(r'(?<=[.!?])\s+', summary_text)
                all_points.extend(s.strip() for s in sentences if s.strip())

            bullets = '\n'.join(f'• {point}' for point in all_points)
            return {
                'summary': bullets,
                'word_count': len(bullets.split()),
                'mode': 'bullets',
                'bullet_count': len(all_points),
            }
        except Exception as e:
            print(f"[Summarizer] Bullet generation error: {e}")

    # Fallback
    sentences = re.split(r'(?<=[.!?])\s+', text)
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at',
        'to', 'for', 'of', 'and', 'or', 'but', 'not', 'with',
    }
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    word_freq = Counter(w for w in words if w not in stop_words)

    scored = []
    for idx, sent in enumerate(sentences):
        sent_words = re.findall(r'\b[a-zA-Z]+\b', sent.lower())
        score = sum(word_freq.get(w, 0) for w in sent_words)
        scored.append((score, idx, sent))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = sorted(scored[:7], key=lambda x: x[1])
    points = [t[2].strip() for t in top if t[2].strip()]
    bullets = '\n'.join(f'• {p}' for p in points)

    return {
        'summary': bullets,
        'word_count': len(bullets.split()),
        'mode': 'bullets',
        'bullet_count': len(points),
        'method': 'extractive_fallback',
    }


def generate_exam_notes(text: str) -> dict:
    """Generate exam-focused study notes with key points, definitions, etc."""
    summarizer = get_summarizer()

    if summarizer is not None:
        try:
            chunks = chunk_text(text)
            summaries: list[str] = []
            for chunk in chunks:
                if len(chunk.split()) < 30:
                    summaries.append(chunk)
                    continue
                result = summarizer(
                    chunk,
                    max_length=250,
                    min_length=80,
                    do_sample=False,
                    truncation=True,
                )
                summaries.append(result[0]['summary_text'])

            combined = ' '.join(summaries)
            sentences = re.split(r'(?<=[.!?])\s+', combined)

            notes_text = '📚 EXAM NOTES\n' + '=' * 40 + '\n\n'
            notes_text += '📌 KEY POINTS:\n'
            for i, s in enumerate(sentences[:10], 1):
                notes_text += f'  {i}. {s.strip()}\n'

            notes_text += f'\n📝 DETAILED SUMMARY:\n{combined}\n'
            notes_text += f'\n📊 STATISTICS:\n'
            notes_text += f'  - Original word count: {len(text.split())}\n'
            notes_text += f'  - Notes word count: {len(combined.split())}\n'

            return {
                'summary': notes_text,
                'word_count': len(notes_text.split()),
                'mode': 'exam_notes',
            }
        except Exception as e:
            print(f"[Summarizer] Exam notes error: {e}")

    # Fallback
    summary = _extractive_summary(text, num_sentences=10)
    sentences = re.split(r'(?<=[.!?])\s+', summary)

    notes_text = '📚 EXAM NOTES\n' + '=' * 40 + '\n\n'
    notes_text += '📌 KEY POINTS:\n'
    for i, s in enumerate(sentences, 1):
        notes_text += f'  {i}. {s.strip()}\n'

    notes_text += f'\n📊 STATISTICS:\n'
    notes_text += f'  - Original word count: {len(text.split())}\n'
    notes_text += f'  - Notes word count: {len(summary.split())}\n'

    return {
        'summary': notes_text,
        'word_count': len(notes_text.split()),
        'mode': 'exam_notes',
        'method': 'extractive_fallback',
    }
