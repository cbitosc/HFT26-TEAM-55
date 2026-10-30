"""Input validation and sanitization helpers for ShopStream."""

import re


def validate_email(email: str) -> bool:
    """Validate email address format against RFC 5322 pattern."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def validate_card_number(card_number: str) -> bool:
    """Validate a credit card number using the Luhn checksum algorithm."""
    clean = re.sub(r"\D", "", card_number)
    if not 13 <= len(clean) <= 19:
        return False

    digits = [int(d) for d in clean]
    checksum = 0
    reverse_digits = digits[::-1]

    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit

    return checksum % 10 == 0


def sanitize_input(text: str) -> str:
    """Remove dangerous HTML/script characters to prevent injection."""
    return re.sub(r"[<>&\"']", "", text.strip())
