"""Shopping cart checkout session calculations and discounts."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from products.inventory import reserve_stock


COUPONS: Dict[str, float] = {
    "WELCOME10": 0.10,
    "SUMMER20": 0.20,
    "BLACKFRIDAY": 0.35,
}


@dataclass
class CartItem:
    product_id: str
    unit_price: float
    quantity: int


@dataclass
class CheckoutSession:
    """Represents a customer's active checkout session."""
    session_id: str
    user_id: str
    items: List[CartItem] = field(default_factory=list)
    coupon_code: Optional[str] = None
    tax_rate: float = 0.08  # 8% sales tax


def calculate_order_total(session: CheckoutSession) -> float:
    """Calculate the final payable order total including discounts and sales tax."""
    subtotal = sum(item.unit_price * item.quantity for item in session.items)

    discount = 0.0
    if session.coupon_code and session.coupon_code in COUPONS:
        discount = subtotal * COUPONS[session.coupon_code]

    taxable = max(0.0, subtotal - discount)
    tax = taxable * session.tax_rate
    return round(taxable + tax, 2)


def apply_discount_coupon(session: CheckoutSession, code: str) -> bool:
    """Validate and attach a coupon code to the checkout session."""
    clean_code = code.strip().upper()
    if clean_code in COUPONS:
        session.coupon_code = clean_code
        return True
    return False
