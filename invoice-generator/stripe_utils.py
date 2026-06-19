"""Stripe Checkout integration.

We never touch raw card data: a hosted Checkout Session is created for the
invoice's balance due and the customer is redirected to Stripe's page.
"""
import stripe

from helpers import currency_symbol


def configure(secret_key):
    stripe.api_key = secret_key


def create_checkout_session(invoice, secret_key, base_url):
    """Create a Stripe Checkout Session for the invoice balance due.

    Returns the ``stripe.checkout.Session`` object. Raises if Stripe is
    not configured or the balance is not positive.
    """
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")

    amount = invoice.balance_due
    if amount <= 0:
        raise ValueError("Invoice has no positive balance due.")

    configure(secret_key)

    # Stripe expects the smallest currency unit (e.g. cents).
    currency = (invoice.currency or "usd").lower()
    unit_amount = int(round(amount * 100))

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": currency,
                    "product_data": {
                        "name": f"Invoice {invoice.invoice_number}",
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }
        ],
        success_url=f"{base_url}/invoice/{invoice.id}?paid=1",
        cancel_url=f"{base_url}/invoice/{invoice.id}?canceled=1",
        metadata={"invoice_id": str(invoice.id)},
    )
    return session


def construct_webhook_event(payload, sig_header, webhook_secret):
    """Verify and parse an incoming Stripe webhook payload."""
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
