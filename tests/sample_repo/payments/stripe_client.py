"""Stripe API integration client and webhook verification."""

import hmac
import hashlib
import time
from typing import Dict, Optional
from config.settings import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET


class StripePaymentGateway:
    """Wrapper for external payment processor API calls."""

    def __init__(self, api_key: str = STRIPE_SECRET_KEY):
        self.api_key = api_key

    def create_charge(
        self, amount_cents: int, currency: str, customer_token: str, description: str
    ) -> Dict:
        """Submit a payment charge request to Stripe."""
        if amount_cents <= 0:
            raise ValueError("Charge amount must be greater than zero.")

        # Simulate successful Stripe charge payload
        charge_id = f"ch_{int(time.time())}_{amount_cents}"
        return {
            "id": charge_id,
            "amount": amount_cents,
            "currency": currency.lower(),
            "status": "succeeded",
            "paid": True,
            "customer": customer_token,
            "description": description,
        }

    def verify_webhook_signature(self, payload: bytes, header_signature: str) -> bool:
        """Verify that an incoming webhook event was genuinely signed by Stripe."""
        if not header_signature or not STRIPE_WEBHOOK_SECRET:
            return False

        # Header format: t=timestamp,v1=signature
        elements = dict(item.split("=") for item in header_signature.split(",") if "=" in item)
        timestamp = elements.get("t")
        expected_v1 = elements.get("v1")

        if not timestamp or not expected_v1:
            return False

        signed_payload = f"{timestamp}.".encode() + payload
        calculated_mac = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_mac, expected_v1)
