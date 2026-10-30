"""Email notification services for transactional messages."""

from typing import Dict, List
from config.settings import SMTP_HOST, SMTP_PORT, SUPPORT_EMAIL


OUTBOX_EMAILS: List[Dict] = []


def send_welcome_email(user_email: str, username: str) -> bool:
    """Send welcome onboarding email to newly registered users."""
    subject = "Welcome to ShopStream!"
    body = (
        f"Hi {username},\n\n"
        "Thank you for joining ShopStream! Discover amazing deals and fast shipping.\n\n"
        f"Best regards,\nThe ShopStream Team ({SUPPORT_EMAIL})"
    )
    OUTBOX_EMAILS.append({"to": user_email, "subject": subject, "body": body})
    return True


def send_order_receipt(user_email: str, order_id: str, total_amount: float) -> bool:
    """Send itemized purchase confirmation receipt to customer."""
    subject = f"Your ShopStream Receipt - Order #{order_id}"
    body = (
        f"Thank you for your purchase!\n"
        f"Order ID: {order_id}\n"
        f"Total Charged: ${total_amount:.2f}\n\n"
        "Your items are being packed and prepared for dispatch."
    )
    OUTBOX_EMAILS.append({"to": user_email, "subject": subject, "body": body})
    return True
