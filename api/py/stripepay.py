"""Stripe Checkout for the $5 supporter coffee.

Session building and event mapping are plain functions so they can be tested without
touching Stripe. The client wrapper is the only part that talks to the network.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping

from py.supportdb import Supporter

try:  # payments stay optional: a missing dep must not take the map API down
    import stripe

    _STRIPE_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only on hosts without stripe
    _STRIPE_AVAILABLE = False

DEFAULT_AMOUNT_CENTS = 500
DEFAULT_CURRENCY = "aud"
DEFAULT_PRODUCT_NAME = "Brisbane Parking supporter coffee"
EMAIL_MAX_LEN = 320
WEBHOOK_TOLERANCE_SECS = 300
# Fixed label so the Dashboard can compare this one checkout flow over time.
INTEGRATION_IDENTIFIER = "bpf_supporter_coffee_qmwvktzp"

PAID_EVENT_TYPES = (
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
)


def amount_cents() -> int:
    raw = os.environ.get("SUPPORT_AMOUNT_CENTS", "").strip()
    try:
        value = int(raw) if raw else DEFAULT_AMOUNT_CENTS
    except ValueError:
        return DEFAULT_AMOUNT_CENTS
    return value if value > 0 else DEFAULT_AMOUNT_CENTS


def currency() -> str:
    return (os.environ.get("SUPPORT_CURRENCY", "").strip() or DEFAULT_CURRENCY).lower()


def product_name() -> str:
    return os.environ.get("SUPPORT_PRODUCT_NAME", "").strip() or DEFAULT_PRODUCT_NAME


def clean_email(raw: str | None) -> str | None:
    """Prefill hint from the browser, so treat it as untrusted text, not as identity."""
    value = (raw or "").strip().lower()
    if not value or len(value) > EMAIL_MAX_LEN:
        return None
    local, _, domain = value.partition("@")
    if not local or "." not in domain or any(c.isspace() for c in value):
        return None
    return value


def build_session_params(
    *,
    amount: int,
    currency_code: str,
    name: str,
    email: str | None = None,
    clerk_user_id: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "mode": "payment",
        "ui_mode": "embedded_page",
        # Success is shown inside the dialog; there is no page to send anyone back to.
        "redirect_on_completion": "never",
        "submit_type": "donate",
        "integration_identifier": INTEGRATION_IDENTIFIER,
        # No payment_method_types: dynamic payment methods are Dashboard-controlled.
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": currency_code,
                    "unit_amount": amount,
                    "product_data": {"name": name},
                },
            }
        ],
    }
    if email:
        params["customer_email"] = email
    if clerk_user_id:
        params["metadata"] = {"clerk_user_id": clerk_user_id}
    return params


def supporter_from_event(event: Mapping[str, Any]) -> Supporter | None:
    """Maps a paid Checkout Session event to a record; ignores everything else."""
    if event.get("type") not in PAID_EVENT_TYPES:
        return None
    session = (event.get("data") or {}).get("object") or {}
    if session.get("payment_status") != "paid":
        return None
    session_id = session.get("id")
    if not isinstance(session_id, str) or not session_id:
        return None
    details = session.get("customer_details") or {}
    metadata = session.get("metadata") or {}
    clerk_user_id = metadata.get("clerk_user_id")
    return Supporter(
        checkout_session_id=session_id,
        clerk_user_id=clerk_user_id if isinstance(clerk_user_id, str) else None,
        email=clean_email(details.get("email")),
        amount_cents=int(session.get("amount_total") or 0),
        currency=str(session.get("currency") or currency()).lower(),
    )


class StripeSupport:
    def __init__(self, secret_key: str, webhook_secret: str) -> None:
        self.secret_key = secret_key.strip()
        self.webhook_secret = webhook_secret.strip()
        self._client: Any = None
        if self.secret_key and _STRIPE_AVAILABLE:
            self._client = stripe.StripeClient(self.secret_key)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def webhook_enabled(self) -> bool:
        return bool(self.webhook_secret) and _STRIPE_AVAILABLE

    def create_session_secret(
        self, *, email: str | None, clerk_user_id: str | None
    ) -> str:
        if self._client is None:
            raise RuntimeError("Stripe is not configured")
        params = build_session_params(
            amount=amount_cents(),
            currency_code=currency(),
            name=product_name(),
            email=email,
            clerk_user_id=clerk_user_id,
        )
        session = self._client.checkout.sessions.create(params=params)
        secret = session.client_secret
        if not secret:
            raise RuntimeError("Stripe returned a session without a client secret")
        return secret

    def parse_webhook(self, payload: bytes, signature: str) -> Mapping[str, Any] | None:
        """Returns None when the signature does not verify, so callers can 400.

        Verifies the header rather than calling `Webhook.construct_event`, which builds a
        typed Event through the global API key this class deliberately does not set.
        """
        if not self.webhook_enabled:
            return None
        try:
            body = payload.decode("utf-8")
            stripe.WebhookSignature.verify_header(
                body, signature, self.webhook_secret, WEBHOOK_TOLERANCE_SECS
            )
            event = json.loads(body)
        except Exception:
            return None
        return event if isinstance(event, dict) else None
