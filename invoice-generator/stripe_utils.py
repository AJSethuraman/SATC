"""Stripe Checkout + Connect integration.

We never touch raw card data: a hosted Checkout Session is created for the
invoice's balance due and the customer is redirected to Stripe's page.

This is a **platform** (Stripe Connect): each user links their own connected
account as a **Standard** account (they sign in to their existing Stripe, or
create one), and payments are charged **directly on that connected account**
(a "direct charge"), so the money lands in the user's own Stripe balance /
bank — not the platform's. The platform optionally takes an
``application_fee_amount`` (off by default; see PLATFORM_FEE_* config).
"""
import stripe

from currencies import decimals_for


def configure(secret_key):
    stripe.api_key = secret_key


# --------------------------------------------------------------------------
# Connect onboarding (Standard)
# --------------------------------------------------------------------------
def create_connect_account(secret_key, email=None):
    """Create a Standard connected account; returns its id (acct_...).

    Standard accounts are full Stripe accounts the user owns and manages from
    their own Stripe Dashboard. We don't request capabilities — a Standard
    account gets card payments automatically once the user finishes setup, and
    Stripe rejects capability requests on Standard accounts.
    """
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")
    configure(secret_key)
    account = stripe.Account.create(
        type="standard",
        email=email or None,
    )
    return account.id


def create_account_link(secret_key, account_id, refresh_url, return_url):
    """Create a one-time onboarding link the user is redirected to.

    For a Standard account this hosted flow lets the user sign in to an
    existing Stripe account or create a new one.
    """
    configure(secret_key)
    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=refresh_url,
        return_url=return_url,
        type="account_onboarding",
    )
    return link.url


def get_account(secret_key, account_id):
    """Retrieve a connected account (to read charges_enabled, etc.)."""
    configure(secret_key)
    return stripe.Account.retrieve(account_id)


# --------------------------------------------------------------------------
# Payments
# --------------------------------------------------------------------------
def _platform_fee_cents(config, amount_cents):
    """Compute the platform's cut for this charge. 0 means no fee (default)."""
    if not config:
        return 0
    pct = float(config.get("PLATFORM_FEE_PERCENT", 0) or 0)
    flat = int(config.get("PLATFORM_FEE_FLAT_CENTS", 0) or 0)
    fee = int(round(amount_cents * pct / 100.0)) + flat
    # Never let the fee meet/exceed the charge.
    return fee if 0 < fee < amount_cents else 0


def to_minor_units(amount, currency):
    """Convert a decimal amount to the integer Stripe expects.

    Stripe takes ``unit_amount`` in the currency's **smallest unit**, and that
    is not always a hundredth. This used to be ``int(round(amount * 100))``
    for every currency, which is right for the ~140 two-decimal currencies and
    wrong by two orders of magnitude for the rest:

    * **JPY has no minor unit** — the smallest unit *is* the yen. A ¥1,500
      invoice was sent to Checkout as ``150000``, and the client was charged
      **¥150,000**. JPY is one of the fourteen currencies the app has always
      offered in account settings, so this was reachable, not theoretical.
      The same 100x overcharge applied to KRW, VND, CLP, ISK and the eleven
      other zero-decimal currencies.
    * **KWD, BHD, OMR and the other three-decimal currencies** went the other
      way: KWD 1.500 became ``150`` fils instead of ``1500`` — the client was
      undercharged tenfold and the invoice never settled.

    The invoice's own total is untouched either way; it is only the number
    handed to the payment processor that was wrong, which is the worst place
    for it to be — the books say one thing and the card says another.

    Caught by tests/test_stripe_minor_units.py.
    """
    return int(round(amount * (10 ** decimals_for(currency))))


def create_checkout_session(
    invoice, secret_key, base_url, connected_account_id, config=None,
    success_url=None, cancel_url=None,
):
    """Create a Checkout Session for the balance due, charged directly on the
    user's connected account so funds go to them.

    Returns the ``stripe.checkout.Session``. Raises if Stripe/Connect isn't
    ready or the balance is not positive.
    """
    if not secret_key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured.")
    if not connected_account_id:
        raise RuntimeError(
            "Connect a Stripe account first to accept payments."
        )

    amount = invoice.balance_due
    if amount <= 0:
        raise ValueError("Invoice has no positive balance due.")

    configure(secret_key)
    currency = (invoice.currency or "usd").lower()
    unit_amount = to_minor_units(amount, currency)

    params = {
        "mode": "payment",
        "line_items": [
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
        "success_url": success_url or f"{base_url}/invoice/{invoice.id}?paid=1",
        "cancel_url": cancel_url or f"{base_url}/invoice/{invoice.id}?canceled=1",
        "metadata": {"invoice_id": str(invoice.id)},
    }

    fee = _platform_fee_cents(config, unit_amount)
    if fee:
        params["payment_intent_data"] = {"application_fee_amount": fee}

    # Direct charge: the Stripe-Account header puts the charge on the
    # connected account, so the money is theirs.
    session = stripe.checkout.Session.create(
        **params, stripe_account=connected_account_id
    )
    return session


def construct_webhook_event(payload, sig_header, webhook_secret):
    """Verify and parse an incoming Stripe webhook payload."""
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
