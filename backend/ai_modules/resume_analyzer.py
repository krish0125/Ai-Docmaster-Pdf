"""Resume Analyzer — uses Gemini AI to provide ATS scoring and improvement
suggestions.  Falls back to keyword-based analysis when Gemini is unavailable.
"""

import re
from config import Config

# ---------------------------------------------------------------------------
# Gemini client (reuses chat_engine's client)
# ---------------------------------------------------------------------------
_GENAI_AVAILABLE = False

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]


def _get_client():
    if not _GENAI_AVAILABLE or not Config.GEMINI_API_KEY:
        return None
    return genai.Client(api_key=Config.GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def get_analysis_prompt(resume_text: str, target_role: str) -> str:
    """Build a comprehensive analysis prompt for Gemini."""
    role_clause = (
        f'The candidate is targeting the role of: {target_role}.'
        if target_role
        else 'No specific target role was provided — give general advice.'
    )

    return f"""You are an expert ATS (Applicant Tracking System) analyst and career coach.
Analyze the following resume and provide a structured evaluation.

{role_clause}

--- RESUME ---
{resume_text[:25000]}
--- END RESUME ---

Respond in EXACTLY this format (use the exact headers):

ATS_SCORE: <number 0-100>

SKILLS_FOUND:
- <skill 1>
- <skill 2>
...

MISSING_SKILLS:
- <skill 1>
- <skill 2>
...

SUGGESTIONS:
1. <suggestion 1>
2. <suggestion 2>
3. <suggestion 3>
4. <suggestion 4>
5. <suggestion 5>

FORMAT_FEEDBACK:
<paragraph about resume format and structure>

OVERALL_ASSESSMENT:
<paragraph with overall assessment and rating out of 10>
"""


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_gemini_response(response_text: str) -> dict:
    """Parse the structured Gemini response into a dict."""
    result: dict = {
        'ats_score': 0,
        'skills_found': [],
        'missing_skills': [],
        'suggestions': [],
        'format_feedback': '',
        'overall_rating': '',
    }

    try:
        # ATS score
        score_match = re.search(r'ATS_SCORE:\s*(\d+)', response_text)
        if score_match:
            result['ats_score'] = min(100, max(0, int(score_match.group(1))))

        # Skills found
        skills_section = re.search(
            r'SKILLS_FOUND:\s*\n(.*?)(?=\nMISSING_SKILLS:)',
            response_text, re.DOTALL,
        )
        if skills_section:
            result['skills_found'] = [
                line.strip().lstrip('- ').strip()
                for line in skills_section.group(1).strip().split('\n')
                if line.strip() and line.strip() != '-'
            ]

        # Missing skills
        missing_section = re.search(
            r'MISSING_SKILLS:\s*\n(.*?)(?=\nSUGGESTIONS:)',
            response_text, re.DOTALL,
        )
        if missing_section:
            result['missing_skills'] = [
                line.strip().lstrip('- ').strip()
                for line in missing_section.group(1).strip().split('\n')
                if line.strip() and line.strip() != '-'
            ]

        # Suggestions
        suggestions_section = re.search(
            r'SUGGESTIONS:\s*\n(.*?)(?=\nFORMAT_FEEDBACK:)',
            response_text, re.DOTALL,
        )
        if suggestions_section:
            result['suggestions'] = [
                re.sub(r'^\d+\.\s*', '', line.strip()).strip()
                for line in suggestions_section.group(1).strip().split('\n')
                if line.strip()
            ]

        # Format feedback
        format_section = re.search(
            r'FORMAT_FEEDBACK:\s*\n(.*?)(?=\nOVERALL_ASSESSMENT:)',
            response_text, re.DOTALL,
        )
        if format_section:
            result['format_feedback'] = format_section.group(1).strip()

        # Overall assessment
        overall_section = re.search(
            r'OVERALL_ASSESSMENT:\s*\n(.*)',
            response_text, re.DOTALL,
        )
        if overall_section:
            result['overall_rating'] = overall_section.group(1).strip()

    except Exception as e:
        print(f"[ResumeAnalyzer] Parse error: {e}")
        result['parse_error'] = str(e)
        result['raw_response'] = response_text

    return result


# ---------------------------------------------------------------------------
# Keyword-based fallback
# ---------------------------------------------------------------------------

_COMMON_SKILLS = {
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust',
    'sql', 'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express',
    'django', 'flask', 'spring', 'docker', 'kubernetes', 'aws', 'azure',
    'gcp', 'git', 'linux', 'mongodb', 'postgresql', 'mysql', 'redis',
    'graphql', 'rest', 'api', 'microservices', 'ci/cd', 'agile', 'scrum',
    'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'nlp',
    'data analysis', 'data science', 'excel', 'powerpoint', 'communication',
    'leadership', 'project management', 'teamwork', 'problem solving',
}

_RESUME_KEYWORDS = {
    'experience', 'education', 'skills', 'projects', 'certifications',
    'summary', 'objective', 'achievements', 'responsibilities',
    'languages', 'contact', 'email', 'phone', 'linkedin', 'github',
}


def _fallback_analysis(resume_text: str, target_role: str) -> dict:
    """Basic keyword-based analysis when Gemini is unavailable."""
    text_lower = resume_text.lower()
    words = set(re.findall(r'\b[\w+#/.]+\b', text_lower))

    found_skills = sorted(_COMMON_SKILLS & words)
    found_sections = sorted(_RESUME_KEYWORDS & words)

    # Basic ATS score heuristic
    score = 30  # base
    score += min(30, len(found_skills) * 3)        # up to 30 for skills
    score += min(20, len(found_sections) * 3)      # up to 20 for sections
    if len(resume_text.split()) > 200:
        score += 10
    if any(kw in text_lower for kw in ('email', 'phone', 'linkedin')):
        score += 10
    score = min(100, score)

    suggestions = [
        'Ensure your resume includes a professional summary at the top.',
        'Use action verbs to describe your experience (e.g., "Developed", "Led", "Implemented").',
        'Quantify your achievements with numbers and percentages where possible.',
        'Tailor your resume to the specific job description you are applying for.',
        'Keep your resume to 1-2 pages for most roles.',
        'Include relevant certifications and training.',
    ]

    return {
        'ats_score': score,
        'skills_found': found_skills,
        'missing_skills': ['Unable to determine without AI analysis — configure GEMINI_API_KEY for full analysis'],
        'suggestions': suggestions,
        'format_feedback': (
            f'Found {len(found_sections)} of {len(_RESUME_KEYWORDS)} common resume sections. '
            f'Detected {len(found_skills)} technical/soft skills. '
            'For detailed format feedback, configure the Gemini API key.'
        ),
        'overall_rating': (
            f'Basic analysis score: {score}/100. '
            'This is a keyword-based estimate. '
            'Set GEMINI_API_KEY in .env for a comprehensive AI-powered analysis.'
        ),
        'method': 'keyword_fallback',
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_resume(resume_text: str, target_role: str = '') -> dict:
    """Analyze a resume and return structured feedback.

    Uses Gemini when available; falls back to keyword matching otherwise.
    """
    if not resume_text or not resume_text.strip():
        return {
            'ats_score': 0,
            'skills_found': [],
            'missing_skills': [],
            'suggestions': ['No resume text was provided.'],
            'format_feedback': 'No content to analyse.',
            'overall_rating': 'N/A',
            'error': 'Empty resume text',
        }

    client = _get_client()
    if client is None:
        return _fallback_analysis(resume_text, target_role)

    try:
        prompt = get_analysis_prompt(resume_text, target_role)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        parsed = _parse_gemini_response(response.text)
        parsed['method'] = 'gemini_ai'
        return parsed
    except Exception as e:
        print(f"[ResumeAnalyzer] Gemini error, using fallback: {e}")
        result = _fallback_analysis(resume_text, target_role)
        result['gemini_error'] = str(e)
        return result
