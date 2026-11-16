"""
Structured Logger with Sensitive Data Masking (app/utils/logger.py)
Automatically masks API keys, access tokens, secrets, and phone numbers in log messages.
"""
import logging
import re
from typing import Any, Dict


SENSITIVE_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "secret",
    "password",
    "hashed_password",
    "doubletick_api_key",
    "meta_access_token",
    "meta_app_secret",
    "webhook_secret",
    "gemini_api_key",
}


def mask_secret(value: str, visible_prefix: int = 4, visible_suffix: int = 3) -> str:
    if not value:
        return ""
    val = str(value).strip()
    if len(val) <= visible_prefix + visible_suffix + 2:
        return "***MASKED***"
    return f"{val[:visible_prefix]}...{val[-visible_suffix:]}"


def mask_phone(phone: str) -> str:
    if not phone:
        return ""
    p = str(phone).strip()
    if len(p) <= 5:
        return "***"
    return f"{p[:4]}****{p[-3:]}"


def sanitize_dict(data: Any) -> Any:
    if isinstance(data, dict):
        sanitized: Dict[str, Any] = {}
        for k, v in data.items():
            key_lower = str(k).lower()
            if any(s in key_lower for s in SENSITIVE_KEYS):
                sanitized[k] = mask_secret(str(v)) if v else ""
            elif key_lower in ("phone", "recipient_phone", "sender_phone", "to") and isinstance(v, str):
                sanitized[k] = mask_phone(v)
            else:
                sanitized[k] = sanitize_dict(v)
        return sanitized
    if isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    return data


class SensitiveDataFilter(logging.Filter):
    TOKEN_REGEX = re.compile(
        r"(Bearer\s+[A-Za-z0-9\-._~+/]+=*|EAA[A-Za-z0-9]+|dt_[A-Za-z0-9_\-]+)",
        re.IGNORECASE,
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.TOKEN_REGEX.sub("[MASKED_CREDENTIAL]", record.msg)
        return True


def get_logger(name: str = "space_consultant") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(SensitiveDataFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
