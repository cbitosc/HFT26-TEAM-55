"""Security and rate-limiting middleware for HTTP requests."""

import time
from typing import Dict, Optional, Tuple
from auth.tokens import verify_token


class RateLimiter:
    """Sliding window in-memory rate limiter per client IP."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}

    def is_allowed(self, client_ip: str) -> bool:
        """Check if client IP is within request allowance."""
        now = time.time()
        timestamps = self._requests.get(client_ip, [])
        # Prune older than window
        timestamps = [t for t in timestamps if now - t < self.window_seconds]
        if len(timestamps) >= self.max_requests:
            return False

        timestamps.append(now)
        self._requests[client_ip] = timestamps
        return True


def authenticate_bearer_token(authorization_header: Optional[str]) -> Tuple[bool, Optional[dict], Optional[str]]:
    """Extract and validate Bearer JWT token from HTTP Authorization header."""
    if not authorization_header or not authorization_header.startswith("Bearer "):
        return False, None, "Missing or malformed Authorization header."

    token = authorization_header[7:].strip()
    payload = verify_token(token)
    if not payload:
        return False, None, "Invalid or expired session token."

    return True, payload, None
