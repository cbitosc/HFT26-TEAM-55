"""User data models and role definitions."""

from dataclasses import dataclass, field
from typing import List, Optional
from utils.crypto import hash_password, verify_password_hash


@dataclass
class User:
    """Represents a registered platform user account."""
    id: str
    username: str
    email: str
    password_hash: str
    roles: List[str] = field(default_factory=lambda: ["customer"])
    is_active: bool = True

    def check_password(self, password: str) -> bool:
        """Verify given password against stored hash."""
        return verify_password_hash(password, self.password_hash)

    def has_role(self, role: str) -> bool:
        """Check if user has an assigned security role."""
        return role in self.roles
