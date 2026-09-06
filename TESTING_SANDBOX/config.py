"""Configuration and privacy utilities for the order rate-limiting service."""

from __future__ import annotations

import re

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_SOCKET_TIMEOUT = 2
MASK_SENSITIVE_DATA = True

_AUTH_HEADER_RE = re.compile(r"(?i)\b(authorization\s*:\s*)(bearer\s+)?([^\s,;]+)")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*")
_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)


def sanitize_log_output(msg: str) -> str:
    """Redact sensitive values from log messages before they leave the process."""

    if not MASK_SENSITIVE_DATA:
        return msg

    sanitized = _AUTH_HEADER_RE.sub(r"\1[REDACTED]", msg)
    sanitized = _BEARER_RE.sub("Bearer [REDACTED]", sanitized)
    sanitized = _IPV4_RE.sub("[REDACTED_IP]", sanitized)
    return sanitized
