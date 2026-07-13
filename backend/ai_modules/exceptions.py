import sys

class GrokAPIError(Exception):
    """Custom exception raised when a Grok API call fails, containing specific error categorizations."""
    def __init__(self, message: str, error_type: str = "unknown", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code

def parse_grok_error(e: Exception, model_name: str = "") -> GrokAPIError:
    """Parse an OpenAI/Grok Exception and return a categorized GrokAPIError."""
    import openai
    error_msg = str(e)
    
    print("=" * 60, file=sys.stderr)
    print(f"[Grok Exception Raised]", file=sys.stderr)
    print(f"Exception Class: {type(e).__name__}", file=sys.stderr)
    print(f"Raw Message: {error_msg}", file=sys.stderr)
    
    status = getattr(e, 'status_code', None)
    code = getattr(e, 'code', None)
    if status is not None:
        print(f"Status Property: {status}", file=sys.stderr)
    if code is not None:
        print(f"Code Property: {code}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    if isinstance(e, openai.AuthenticationError):
        return GrokAPIError("Invalid Grok API key. Please check your API key.", "invalid_key", 503)
    elif isinstance(e, openai.PermissionDeniedError):
        return GrokAPIError("Grok API access forbidden. Ensure you have credits.", "forbidden", 503)
    elif isinstance(e, openai.RateLimitError):
        return GrokAPIError("Grok API quota exceeded. Please wait a minute.", "quota_exceeded", 503)
    elif isinstance(e, openai.NotFoundError):
        return GrokAPIError(f"Grok model not found or invalid: {model_name}.", "model_not_found", 503)
    elif isinstance(e, openai.APITimeoutError):
        return GrokAPIError("Connection to Grok API timed out.", "timeout", 503)
    else:
        return GrokAPIError(f"Grok API call failed: {error_msg}", "network", 503)

def call_grok_with_retry(client, model: str, messages: list, **kwargs):
    """Call OpenAI chat completion with exponential backoff on 429 and 5xx errors."""
    import time
    import openai
    max_retries = 3
    wait_time = 3.0
    
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return response
        except Exception as e:
            is_429 = isinstance(e, openai.RateLimitError)
            is_5xx = isinstance(e, openai.InternalServerError)
            
            if (is_429 or is_5xx) and attempt < max_retries:
                print(f"[Grok Retry] Attempt {attempt + 1}/{max_retries} failed. Retrying...", file=sys.stderr)
                time.sleep(wait_time)
                wait_time *= 2
                continue
            
            if is_429:
                raise GrokAPIError("AI service is busy.", "quota_exceeded", 503)
            else:
                raise parse_grok_error(e, model_name=model)
