"""Core HTTP endpoints dispatching to domain services."""

from auth.login import login_user, logout_user
from auth.register import register_new_user
from payments.checkout import CheckoutSession, calculate_order_total, apply_discount_coupon
from payments.stripe_client import StripePaymentGateway
from notifications.email_sender import send_order_receipt
from api.middleware import RateLimiter, authenticate_bearer_token

rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
gateway = StripePaymentGateway()


def handle_login(request_data: dict, client_ip: str) -> dict:
    """Route handler for user login credentials verification."""
    if not rate_limiter.is_allowed(client_ip):
        return {"status": "error", "message": "Rate limit exceeded"}

    email = request_data.get("email", "")
    password = request_data.get("password", "")
    success, token, error = login_user(email, password)
    if not success:
        return {"status": "error", "message": error}

    return {"status": "ok", "token": token}


def handle_checkout(session: CheckoutSession, customer_token: str, user_email: str) -> dict:
    """Route handler for finalizing checkout and charging customer via Stripe."""
    total = calculate_order_total(session)
    amount_cents = int(total * 100)

    try:
        charge = gateway.create_charge(
            amount_cents=amount_cents,
            currency="usd",
            customer_token=customer_token,
            description=f"Order {session.session_id}",
        )
        send_order_receipt(user_email, session.session_id, total)
        return {"status": "ok", "charge": charge, "total": total}
    except Exception as e:
        return {"status": "error", "message": str(e)}
