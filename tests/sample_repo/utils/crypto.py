"""Cryptographic utilities for password hashing and secure token generation."""

import hashlib
import hmac
import secrets


def hash_password(password: str, salt: str = "") -> str:
    """Hash a plaintext password using SHA-256 with optional salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${hashed}"


def verify_password_hash(plain_password: str, stored_hash: str) -> bool:
    """Verify that a plaintext password matches the stored salted hash."""
    if "$" not in stored_hash:
        return False
    salt, expected = stored_hash.split("$", 1)
    recalculated = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(recalculated, expected)


def generate_random_token(byte_length: int = 32) -> str:
    """Generate a cryptographically secure URL-safe random string."""
    return secrets.token_urlsafe(byte_length)
