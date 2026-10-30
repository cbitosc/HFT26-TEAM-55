"""User onboarding and registration logic."""

import uuid
from typing import Optional, Tuple
from auth.models import User
from auth.login import _USER_STORE
from utils.crypto import hash_password
from utils.validators import validate_email, sanitize_input


def register_new_user(
    username: str, email: str, password: str
) -> Tuple[bool, Optional[User], Optional[str]]:
    """Register a new customer account after validating inputs and email uniqueness."""
    clean_username = sanitize_input(username)
    clean_email = email.strip().lower()

    if not validate_email(clean_email):
        return False, None, "Invalid email address format."

    if len(password) < 8:
        return False, None, "Password must be at least 8 characters long."

    if clean_email in _USER_STORE:
        return False, None, "An account with this email already exists."

    user_id = str(uuid.uuid4())
    hashed_pw = hash_password(password)

    new_user = User(
        id=user_id,
        username=clean_username,
        email=clean_email,
        password_hash=hashed_pw,
        roles=["customer"],
    )

    _USER_STORE[clean_email] = new_user
    return True, new_user, None
