"""Mobile push notifications and device token management."""

from typing import Dict, List, Set


_DEVICE_TOKENS: Dict[str, Set[str]] = {}
PUSH_DELIVERIES: List[Dict] = []


def register_device_token(user_id: str, device_token: str) -> None:
    """Associate a mobile push device token with a user account."""
    if user_id not in _DEVICE_TOKENS:
        _DEVICE_TOKENS[user_id] = set()
    _DEVICE_TOKENS[user_id].add(device_token)


def send_push_notification(user_id: str, title: str, message: str) -> int:
    """Deliver push notification to all active devices registered by the user."""
    tokens = _DEVICE_TOKENS.get(user_id, set())
    delivered = 0

    for token in tokens:
        record = {
            "token": token,
            "user_id": user_id,
            "title": title,
            "message": message,
        }
        PUSH_DELIVERIES.append(record)
        delivered += 1

    return delivered
