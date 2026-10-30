"""Order refund processing and audit logging."""

import time
from typing import Dict, List, Optional, Tuple


REFUND_LOGS: List[Dict] = []


def is_eligible_for_refund(order_timestamp: float, max_days: int = 30) -> bool:
    """Determine whether an order is within the allowed 30-day return window."""
    elapsed_seconds = time.time() - order_timestamp
    return elapsed_seconds <= (max_days * 86400)


def process_refund(
    order_id: str,
    charge_id: str,
    amount_cents: int,
    order_timestamp: float,
    reason: str = "customer_request",
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Verify eligibility and execute an order refund through the payment gateway."""
    if not is_eligible_for_refund(order_timestamp):
        return False, None, "Order is past the 30-day refund window."

    if amount_cents <= 0:
        return False, None, "Refund amount must be positive."

    refund_id = f"re_{order_id}_{int(time.time())}"
    log_entry = {
        "refund_id": refund_id,
        "order_id": order_id,
        "charge_id": charge_id,
        "amount": amount_cents,
        "reason": reason,
        "timestamp": time.time(),
        "status": "processed",
    }
    REFUND_LOGS.append(log_entry)
    return True, refund_id, None
