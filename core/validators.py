"""
core/validators.py
------------------
Input sanitization and validation utilities for CampusLink 2.0.
"""
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
UMAT_DOMAINS = ("umat.edu.gh", "student.umat.edu.gh", "st.umat.edu.gh")

def validate_email(email: str) -> bool:
    """Validates email format and institutional domain structure."""
    if not email or not isinstance(email, str):
        return False
    clean = email.strip()
    if not EMAIL_REGEX.match(clean):
        return False
    return True

def sanitize_text(text: Optional[str], max_length: int = 500) -> str:
    """Sanitizes user text input, trimming whitespace and stripping dangerous control characters."""
    if text is None:
        return ""
    # Strip null bytes and control chars
    clean = "".join(ch for ch in str(text) if ch.isprintable() or ch in ('\n', '\r', '\t'))
    clean = clean.strip()
    return clean[:max_length]

def validate_monetary_amount(amount) -> Optional[Decimal]:
    """Validates that a value is a non-negative monetary Decimal."""
    try:
        val = Decimal(str(amount))
        if val < Decimal("0.00"):
            return None
        return val.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None
