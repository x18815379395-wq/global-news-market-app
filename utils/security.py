import re


def redact_secrets(text: str) -> str:
    """Redact common secret patterns from logs and error strings."""
    if not isinstance(text, str):
        return text

    redacted = text

    # Query params like apiKey=, apikey=, api_key=, key=, token=, secret=
    redacted = re.sub(r"(?i)(api[_-]?key|key|token|secret)=([^&\s]+)", r"\1=***REDACTED***", redacted)

    # Authorization: Bearer <token>
    redacted = re.sub(r"(?i)Authorization:\s*Bearer\s+[A-Za-z0-9._\-]+", "Authorization: Bearer ***REDACTED***", redacted)

    # Generic bearer tokens without header prefix
    redacted = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._\-]+", "Bearer ***REDACTED***", redacted)

    # URLs that include secrets (best-effort)
    redacted = re.sub(r"(?i)(https?://[^\s?]+\?(?:[^\s]*))(api[_-]?key|key|token|secret)=([^&\s]+)", r"\1\2=***REDACTED***", redacted)

    return redacted


def is_configured_key(value: str) -> bool:
    """Return True if an env var-like key is configured (not empty or placeholder)."""
    if not value:
        return False
    s = value.strip()
    if not s:
        return False
    return ('YOUR_' not in s) and ('your_' not in s)

