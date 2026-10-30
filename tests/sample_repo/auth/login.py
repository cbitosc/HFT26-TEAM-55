"""Authentication handler for user login and session termination."""

from typing import Dict, Optional, Tuple
from auth.models import User
from auth.tokens import create_access_token, revoke_token
from utils.crypto import verify_password_hash

# Mock user database for demonstration
_USER_STORE: Dict[str, User] = {}


def login_user(email: str, password: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Authenticate user credentials and return a signed JWT token on success.

    Returns:
        (success: bool, token_or_none: str, error_message: str)
    """
    user = _USER_STORE.get(email.strip().lower())
    if not user:
        return False, None, "Invalid email or password."

    if not user.is_active:
        return False, None, "User account is suspended."

    if not verify_password_hash(password, user.password_hash):
        return False, None, "Invalid email or password."

    token = create_access_token(user.id, user.email, user.roles)
    return True, token, None


def logout_user(token: str) -> bool:
    """Log out a user by invalidating the current active JWT session token."""
    revoke_token(token)
    return True
