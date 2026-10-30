"""JSON Web Token (JWT) encoding, verification, and revocation."""

import time
import base64
import json
import hmac
import hashlib
from typing import Dict, Optional
from config.settings import JWT_SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES


_REVOKED_TOKENS = set()


def create_access_token(user_id: str, email: str, roles: list) -> str:
    """Generate a signed JWT token containing user identity and expiration claims."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles,
        "iat": int(time.time()),
        "exp": int(time.time()) + (ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    }

    hdr_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    unsigned = f"{hdr_b64}.{payload_b64}"

    signature = hmac.new(
        JWT_SECRET_KEY.encode(), unsigned.encode(), hashlib.sha256
    ).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    return f"{unsigned}.{sig_b64}"


def verify_token(token: str) -> Optional[Dict]:
    """Verify JWT signature, check expiration time, and ensure token is not revoked."""
    if token in _REVOKED_TOKENS:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    hdr_b64, payload_b64, sig_b64 = parts
    unsigned = f"{hdr_b64}.{payload_b64}"

    expected_sig = base64.urlsafe_b64encode(
        hmac.new(JWT_SECRET_KEY.encode(), unsigned.encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()

    if not hmac.compare_digest(sig_b64, expected_sig):
        return None

    try:
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None  # Token expired
        return payload
    except Exception:
        return None


def revoke_token(token: str) -> None:
    """Add a JWT token to the blacklist/revocation set."""
    _REVOKED_TOKENS.add(token)
