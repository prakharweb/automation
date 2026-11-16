"""
Phone Number Normalization & Validation Utility (app/utils/phone.py)
Normalizes phone numbers from Meta Instant Forms into international E.164 format
required by DoubleTick WhatsApp Business API.
"""
import re
from typing import Optional


def normalize_phone_number(raw_phone: Optional[str], default_country_code: str = "91") -> Optional[str]:
    if not raw_phone:
        return None
    cleaned = str(raw_phone).strip()
    if not cleaned:
        return None

    has_plus = cleaned.startswith("+")
    digits = re.sub(r"\D", "", cleaned)
    if not digits:
        return None

    # Strip leading 00 international prefix
    if digits.startswith("00") and len(digits) > 10:
        digits = digits[2:]
        has_plus = True

    # Handle 11-digit Indian domestic number with leading 0 (e.g., 09876543210)
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    # Handle 10-digit Indian mobile number (starts with 6-9)
    if len(digits) == 10:
        digits = f"{default_country_code}{digits}"

    # Validate plausible international phone length (10 to 15 digits per E.164)
    if len(digits) < 10 or len(digits) > 15:
        return None

    return f"+{digits}" if (has_plus or len(digits) >= 11) else f"+{digits}"
