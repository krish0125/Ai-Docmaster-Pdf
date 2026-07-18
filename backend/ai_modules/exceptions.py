import sys

class GeminiAPIError(Exception):
    """Custom exception raised when a Gemini API call fails, containing specific error categorizations."""
    def __init__(self, message: str, error_type: str = "unknown", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code

def parse_gemini_error(e: Exception, model_name: str = "") -> GeminiAPIError:
    """Parse a google-genai Exception and return a categorized GeminiAPIError.
    
    google-genai 2.6.0 error hierarchy:
      APIError (base)
        ├─ ClientError  (4xx — has .status property)
        └─ ServerError  (5xx — has .status property)
    """
    from google.genai import errors as genai_errors

    error_msg = str(e)

    print("=" * 60, file=sys.stderr)
    print(f"[Gemini Exception Raised]", file=sys.stderr)
    print(f"Exception Class: {type(e).__name__}", file=sys.stderr)
    print(f"Raw Message: {error_msg}", file=sys.stderr)

    # Use .status if available (ClientError / ServerError both have it)
    http_status = getattr(e, 'status', getattr(e, 'code', None))
    if http_status is not None:
        try:
            http_status = int(http_status)
        except (ValueError, TypeError):
            pass
        print(f"HTTP Status: {http_status}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Resolve by HTTP status code first (most reliable)
    if http_status == 401 or "API_KEY_INVALID" in error_msg or "UNAUTHENTICATED" in error_msg:
        return GeminiAPIError("Invalid Gemini API key. Please check your API key.", "invalid_key", 401)
    elif http_status == 403 or "PERMISSION_DENIED" in error_msg:
        return GeminiAPIError("Gemini API access forbidden. Ensure your API key has the right permissions.", "forbidden", 403)
    elif http_status == 429 or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
        return GeminiAPIError("Gemini API quota exceeded. Please wait a minute.", "quota_exceeded", 429)
    elif http_status == 400 or "INVALID_ARGUMENT" in error_msg:
        return GeminiAPIError(f"Gemini API bad request: {error_msg}", "bad_request", 400)
    elif http_status in (404, 400) or "model not found" in error_msg.lower() or "NOT_FOUND" in error_msg:
        return GeminiAPIError(f"Gemini model not found or invalid: {model_name}. Details: {error_msg}", "model_not_found", 404)
    elif http_status == 504 or "timeout" in error_msg.lower() or "DEADLINE_EXCEEDED" in error_msg:
        return GeminiAPIError("Connection to Gemini API timed out.", "timeout", 504)
    elif isinstance(e, genai_errors.ServerError) or (isinstance(http_status, int) and http_status >= 500):
        return GeminiAPIError("Gemini API is temporarily unavailable.", "service_unavailable", 503)
    elif isinstance(e, genai_errors.ClientError):
        return GeminiAPIError(f"Gemini API client error: {error_msg}", "bad_request", http_status or 400)
    else:
        return GeminiAPIError(f"Gemini API call failed: {error_msg}", "network", 503)

def call_gemini_with_retry(client, model: str, contents, **kwargs):
    """Call google-genai generate_content with exponential backoff on 429 and 5xx errors."""
    import time
    from google.genai import errors as genai_errors

    max_retries = 3
    wait_time = 3.0

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                **kwargs
            )
            return response
        except Exception as e:
            http_status = getattr(e, 'status', getattr(e, 'code', None))
            if http_status is not None:
                try:
                    http_status = int(http_status)
                except (ValueError, TypeError):
                    pass
            
            error_msg = str(e)
            is_429 = http_status == 429 or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower()
            is_5xx = isinstance(e, genai_errors.ServerError) or (isinstance(http_status, int) and http_status >= 500)
            is_retryable = is_429 or is_5xx

            if is_retryable and attempt < max_retries:
                print(f"[Gemini Retry] Attempt {attempt + 1}/{max_retries} failed (status={http_status}). "
                      f"Retrying in {wait_time:.0f}s...", file=sys.stderr)
                time.sleep(wait_time)
                wait_time *= 2
                continue

            if is_429:
                raise GeminiAPIError("Gemini AI service is busy. Please try again later.", "quota_exceeded", 503)
            else:
                raise parse_gemini_error(e, model_name=model)
