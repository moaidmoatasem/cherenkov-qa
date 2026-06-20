"""
cherenkov/security/redact.py — PII & secrets redaction for traces, logs, and agent memory.

Scans any string or nested dict/list for PII patterns (email, phone, SSN, credit
card, API keys, passwords, bearer tokens) and replaces matches with typed
placeholders. Plugs into the Logfire tracer, agent memory writer, and any
persistent store that holds free-text user data.

Usage:
    from cherenkov.security.redact import redact, redact_dict

    safe_text = redact(user_input)
    safe_record = redact_dict(trace_span)
"""

from __future__ import annotations

import re
from typing import Any


# ── Pattern registry ────────────────────────────────────────────────────────
# Each entry: (label, compiled pattern, replacement)
# Patterns ordered from most-specific to least-specific so overlap is handled.

_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # API keys / secrets — must come FIRST (long, high-entropy)
    (
        "api_key",
        re.compile(
            r'\b(?:sk|pk|rk|ak|ek|api|token|key)[-_]?[A-Za-z0-9]{20,}\b',
            re.IGNORECASE,
        ),
        "[REDACTED:api_key]",
    ),
    # Bearer / Authorization header values
    (
        "bearer_token",
        re.compile(
            r'(?:Bearer|Basic|Token)\s+[A-Za-z0-9+/=._-]{10,}',
            re.IGNORECASE,
        ),
        "[REDACTED:bearer_token]",
    ),
    # AWS access key ID
    (
        "aws_access_key",
        re.compile(r'\b(?:AKIA|AIPA|AIDA|AROA|ASIA)[A-Z0-9]{16}\b'),
        "[REDACTED:aws_access_key]",
    ),
    # AWS secret access key (40 chars, base64-ish)
    (
        "aws_secret_key",
        re.compile(r'(?<![A-Za-z0-9/+])[A-Za-z0-9/+]{40}(?![A-Za-z0-9/+])'),
        "[REDACTED:aws_secret_key]",
    ),
    # Credit card numbers (Luhn-layout, 13-16 digits with optional spaces/dashes)
    (
        "credit_card",
        re.compile(
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?'        # Visa
            r'|5[1-5][0-9]{14}'                      # MasterCard
            r'|3[47][0-9]{13}'                       # Amex
            r'|6(?:011|5[0-9]{2})[0-9]{12}'         # Discover
            r'|(?:\d[ -]?){13,16})\b',
            re.VERBOSE,
        ),
        "[REDACTED:credit_card]",
    ),
    # US SSN
    (
        "ssn",
        re.compile(r'\b\d{3}[-\s]\d{2}[-\s]\d{4}\b'),
        "[REDACTED:ssn]",
    ),
    # Email addresses
    (
        "email",
        re.compile(
            r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b',
            re.IGNORECASE,
        ),
        "[REDACTED:email]",
    ),
    # Phone numbers (E.164, US/international formats)
    (
        "phone",
        re.compile(
            r'(?<!\d)(?:\+?1[-.\s]?)?'
            r'(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]\d{4}(?!\d)',
        ),
        "[REDACTED:phone]",
    ),
    # IPv4 addresses (private ranges are still PII in logs)
    (
        "ipv4",
        re.compile(
            r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}'
            r'(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b',
        ),
        "[REDACTED:ipv4]",
    ),
    # Passwords in JSON / query strings: "password": "...", password=...
    (
        "password_field",
        re.compile(
            r'(?i)(?:"(?:password|passwd|pass|secret|pwd|credential)"\s*:\s*")'
            r'([^"]{1,256})',
        ),
        r'[REDACTED:password]"',
    ),
]

# Field names whose *values* should always be fully redacted regardless of content.
_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "password", "passwd", "pass", "secret", "api_key", "apikey",
        "access_key", "secret_key", "token", "auth_token", "refresh_token",
        "private_key", "client_secret", "ssn", "credit_card", "card_number",
        "cvv", "pin", "dob", "date_of_birth", "national_id",
    }
)


def redact(text: str, *, label_pii: bool = True) -> str:
    """Scan *text* for PII/secret patterns and return a redacted copy.

    Args:
        text: The string to scan.
        label_pii: If True (default) replace matches with typed placeholders
            like ``[REDACTED:email]``. If False use a single ``[REDACTED]``.

    Returns:
        A new string with all detected PII replaced.
    """
    if not isinstance(text, str) or not text:
        return text
    result = text
    for label, pattern, placeholder in _PATTERNS:
        replacement = placeholder if label_pii else "[REDACTED]"
        try:
            result = pattern.sub(replacement, result)
        except re.error:
            pass
    return result


def redact_dict(data: Any, *, label_pii: bool = True) -> Any:
    """Recursively redact PII from a nested dict / list / string.

    - Dict values whose key is in ``_SENSITIVE_KEYS`` are fully replaced.
    - All string values are passed through :func:`redact`.
    - Lists and nested dicts are traversed.
    - Non-string scalars (int, float, bool, None) are returned unchanged.
    """
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS:
                out[k] = "[REDACTED:sensitive_field]"
            else:
                out[k] = redact_dict(v, label_pii=label_pii)
        return out
    if isinstance(data, list):
        return [redact_dict(item, label_pii=label_pii) for item in data]
    if isinstance(data, str):
        return redact(data, label_pii=label_pii)
    return data


def is_clean(text: str) -> bool:
    """Return True if *text* contains no detectable PII.

    Useful for assertion gates: ``assert is_clean(trace_body)``.
    """
    return redact(text) == text


class PIIRedactingFormatter:
    """Wraps a log formatter and redacts PII from every log message.

    Compatible with Python's ``logging.Formatter`` contract — pass as a
    ``formatter`` to any ``logging.Handler``.

        import logging
        from cherenkov.security.redact import PIIRedactingFormatter

        handler = logging.StreamHandler()
        handler.setFormatter(PIIRedactingFormatter())
        logging.getLogger().addHandler(handler)
    """

    def format(self, record: Any) -> str:
        if hasattr(record, "getMessage"):
            record.msg = redact(str(record.getMessage()))
            record.args = ()
        return str(record.msg)
