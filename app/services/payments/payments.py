"""
Payment providers: Dummy (dev), Stripe, Razorpay.
Tenant chooses provider in Settings → Payments; credentials come from payment_config.
"""
from __future__ import annotations
import logging
import uuid
from dataclasses import dataclass

from app.services.db import get_db
from app.core.container import get_tenant_service

logger = logging.getLogger(__name__)


@dataclass
class PaymentIntent:
    intent_id: str
    payment_url: str


class PaymentsProvider:
    """Base for payment providers. Implement create_intent and name."""

    def __init__(self, tenant: str):
        self.tenant = tenant

    def create_intent(self, order_id: str, amount: float, currency: str) -> PaymentIntent:
        raise NotImplementedError

    def name(self) -> str:
        raise NotImplementedError


def _persist_payment(tenant: str, order_id: str, provider_name: str, intent_id: str, amount: float, currency: str) -> None:
    db = get_db()
    db.get_collection("payments").insert_one({
        "tenant": tenant,
        "order_id": order_id,
        "provider": provider_name,
        "intent_id": intent_id,
        "amount": float(amount),
        "currency": currency,
        "status": "pending",
        "events": [],
    })


class DummyProvider(PaymentsProvider):
    """Dev/test provider; no real charges."""

    def name(self) -> str:
        return "dummy"

    def create_intent(self, order_id: str, amount: float, currency: str) -> PaymentIntent:
        intent_id = f"dummy_{uuid.uuid4().hex[:12]}"
        url = f"https://example.com/pay/{intent_id}"
        _persist_payment(self.tenant, order_id, self.name(), intent_id, amount, currency)
        return PaymentIntent(intent_id=intent_id, payment_url=url)


class StripeProvider(PaymentsProvider):
    """Stripe: uses payment_config.stripe_secret_key. Create PaymentIntent and return client_secret URL or checkout URL."""

    def name(self) -> str:
        return "stripe"

    def create_intent(self, order_id: str, amount: float, currency: str) -> PaymentIntent:
        try:
            import stripe
        except ImportError:
            logger.warning("stripe not installed; add stripe to requirements")
            return DummyProvider(self.tenant).create_intent(order_id, amount, currency)
        settings = get_tenant_service().get_tenant_settings(self.tenant) or {}
        pay = settings.get("payment_config") or {}
        secret = (pay.get("stripe_secret_key") or pay.get("secret_key") or "").strip()
        if not secret:
            logger.warning("Stripe provider selected but stripe_secret_key not set for tenant %s", self.tenant)
            return DummyProvider(self.tenant).create_intent(order_id, amount, currency)
        stripe.api_key = secret
        amount_cents = max(1, int(round(amount * 100)))
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=(currency or "inr").lower(),
            metadata={"order_id": order_id, "tenant": self.tenant},
        )
        intent_id = intent.id
        _persist_payment(self.tenant, order_id, self.name(), intent_id, amount, currency)
        return PaymentIntent(intent_id=intent_id, payment_url=f"https://dashboard.stripe.com/test/payments/{intent_id}")


class RazorpayProvider(PaymentsProvider):
    """Razorpay: uses payment_config.razorpay_key_id and razorpay_key_secret. Create order and return payment URL."""

    def name(self) -> str:
        return "razorpay"

    def create_intent(self, order_id: str, amount: float, currency: str) -> PaymentIntent:
        try:
            import razorpay
        except ImportError:
            logger.warning("razorpay not installed; add razorpay to requirements")
            return DummyProvider(self.tenant).create_intent(order_id, amount, currency)
        settings = get_tenant_service().get_tenant_settings(self.tenant) or {}
        pay = settings.get("payment_config") or {}
        key_id = (pay.get("razorpay_key_id") or pay.get("key_id") or "").strip()
        key_secret = (pay.get("razorpay_key_secret") or pay.get("key_secret") or "").strip()
        if not key_id or not key_secret:
            logger.warning("Razorpay provider selected but keys not set for tenant %s", self.tenant)
            return DummyProvider(self.tenant).create_intent(order_id, amount, currency)
        client = razorpay.Client(auth=(key_id, key_secret))
        amount_paise = max(1, int(round(amount * 100)))
        data = client.order.create({"amount": amount_paise, "currency": (currency or "INR"), "receipt": order_id})
        intent_id = data["id"]
        _persist_payment(self.tenant, order_id, self.name(), intent_id, amount, currency)
        return PaymentIntent(intent_id=intent_id, payment_url=f"https://dashboard.razorpay.com/app/orders/{intent_id}")


def get_payments_provider(tenant: str) -> PaymentsProvider:
    """Return the payment provider for the tenant (dummy, stripe, or razorpay) from payment_config."""
    cfg = get_tenant_service().get_tenant_settings(tenant) or {}
    pay = cfg.get("payment_config") or {}
    provider = (pay.get("provider") or "dummy").lower()
    if provider == "stripe":
        return StripeProvider(tenant)
    if provider == "razorpay":
        return RazorpayProvider(tenant)
    return DummyProvider(tenant)
