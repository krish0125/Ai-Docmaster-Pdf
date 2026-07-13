import sys

class GeminiAPIError(Exception):
    """Custom exception raised when a Gemini API call fails, containing specific error categorizations."""
    def __init__(self, message: str, error_type: str = "unknown", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_type = error_type      # e.g., 'invalid_key', 'quota_exceeded', 'model_not_found', 'timeout', 'network'
        self.status_code = status_code

def parse_gemini_error(e: Exception, model_name: str = "") -> GeminiAPIError:
    """Parse a Google GenAI Exception and return a categorized GeminiAPIError."""
    error_msg = str(e)
    
    # Print the real exception details to the Flask console
    print("=" * 60, file=sys.stderr)
    print(f"[Gemini Exception Raised]", file=sys.stderr)
    print(f"Exception Class: {type(e).__name__}", file=sys.stderr)
    print(f"Raw Message: {error_msg}", file=sys.stderr)
    
    # Try to extract code or status attributes if they exist
    status = getattr(e, 'status', None)
    code = getattr(e, 'code', None)
    if status is not None:
        print(f"Status Property: {status}", file=sys.stderr)
    if code is not None:
        print(f"Code Property: {code}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # Categorize the error
    if "API_KEY_INVALID" in error_msg or "401" in error_msg:
        return GeminiAPIError(
            message="Invalid Gemini API key. Please check your API key in the configuration.",
            error_type="invalid_key",
            status_code=503
        )
    elif "403" in error_msg:
        return GeminiAPIError(
            message="Gemini API access forbidden. Ensure the Generative Language API is enabled.",
            error_type="forbidden",
            status_code=503
        )
    elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
        return GeminiAPIError(
            message="Gemini API quota exceeded (Rate Limit). Please wait a minute or configure your own API key in the profile settings.",
            error_type="quota_exceeded",
            status_code=503
        )
    elif "404" in error_msg or "not found" in error_msg.lower():
        model_part = f" for model '{model_name}'" if model_name else ""
        return GeminiAPIError(
            message=f"Gemini model not found or invalid{model_part}.",
            error_type="model_not_found",
            status_code=503
        )
    elif "timeout" in error_msg.lower() or "connect" in error_msg.lower() or "host" in error_msg.lower():
        return GeminiAPIError(
            message="Connection to Gemini API timed out or could not be established. Check your internet connection.",
            error_type="timeout",
            status_code=503
        )
    else:
        # Fallback to general API error or network
        return GeminiAPIError(
            message=f"Gemini API call failed: {error_msg}",
            error_type="network",
            status_code=503
        )

def call_gemini_with_retry(client, model: str, contents, **kwargs):
    """Call generate_content with exponential backoff on 429 and 5xx errors."""
    import time
    max_retries = 3
    wait_time = 3.0  # initial wait in seconds
    
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                **kwargs
            )
            return response
        except Exception as e:
            error_msg = str(e)
            
            # Check if it is a 429 or 5xx error
            is_429 = "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg
            is_5xx = "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg or "ServerError" in error_msg or "INTERNAL" in error_msg
            
            if (is_429 or is_5xx) and attempt < max_retries:
                # Log retry attempt to console
                print(f"[Gemini Retry] Attempt {attempt + 1}/{max_retries} failed due to "
                      f"{'429 Rate Limit' if is_429 else '5xx Server Error'}. "
                      f"Waiting {wait_time}s before retrying...", file=sys.stderr)
                time.sleep(wait_time)
                wait_time *= 2  # exponential backoff: 3s -> 6s -> 12s
                continue
            
            # If we run out of retries, or it's a non-retryable error
            if is_429:
                raise GeminiAPIError(
                    message="AI service is busy, please try again in a few seconds.",
                    error_type="quota_exceeded",
                    status_code=503
                )
            else:
                raise parse_gemini_error(e, model_name=model)

