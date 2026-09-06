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

#: CURRENCIES THIS ADAPTER WILL NOT CHARGE IN, and why that is the safe answer.
#:
#: Stripe's per-currency *charge* exponent is not always ISO 4217's, and four
#: currencies are genuinely disputed between the sources available here:
#:
#:   HUF  ISO 2. `currencies.py` records "Stripe treats HUF as zero-decimal
#:        FOR PAYOUTS" -- a payout rule, which an earlier version of this file
#:        wrongly encoded as a charge exponent. That sent HUF 1,500.00 as
#:        `1500` and would have charged the client HUF 15.00.
#:   TWD  ISO 2, "Stripe requires whole-dollar amounts" -- which may mean an
#:        exponent of 0, or 2 with the amount divisible by 100. Not the same
#:        thing, and the difference is a factor of a hundred.
#:   MGA  ISO 2, Stripe zero-decimal. Charging it on the ISO rule sent Ar1,500
#:        as 150000 and charged Ar150,000.
#:   ISK  ISO 0, and Stripe is reported to want 1,500 ISK as `150000`. The
#:        inverse of MGA.
#:
#: Every one of those is a 100x error on a client's card, in one direction or
#: the other, and each is invisible in our own books because the inbound decode
#: applies the same wrong rule and reads the right number back.
#:
#: `docs.stripe.com` is not reachable from this environment, so the exponents
#: could not be settled against the primary source. Guessing them from prose in
#: a code comment is what produced the HUF error in the first place.
#:
#: SO THE ADAPTER REFUSES. An invoice can be RAISED, printed and emailed in any
#: of the 157 currencies -- the document is just a document. Only taking
#: payment is blocked, and only for these four, with a message that says why.
#: docs/DESIGN-PRINCIPLES.md: refuse rather than default. A refusal the owner
#: can read is recoverable; a silent 100x mischarge is not.
#:
#: To lift this: confirm each exponent against Stripe's own currency
#: documentation, add it to a charge-exponent table, and delete the entry here.
UNSETTLED_CHARGE_EXPONENT = {
    "huf": "Stripe's charge exponent for HUF is not confirmed here (its "
           "zero-decimal rule is documented for payouts, not charges).",
    "twd": "Stripe's charge exponent for TWD is not confirmed here "
           "(\"whole-dollar amounts\" may mean 0 places, or 2 divisible by 100).",
    "mga": "Stripe treats MGA as zero-decimal while ISO 4217 records 2, and "
           "the charge exponent is not confirmed here.",
    "isk": "Stripe is reported to charge ISK with 2 places while ISO 4217 "
           "records 0, and this is not confirmed here.",
}


class UnsupportedCurrency(RuntimeError):
    """Raised rather than charge an amount we cannot be sure of."""


def guard_chargeable(currency):
    """Refuse a currency whose Stripe charge exponent is not settled."""
    code = (currency or "usd").lower()
    if code in UNSETTLED_CHARGE_EXPONENT:
        raise UnsupportedCurrency(
            f"Online payment is not available for {code.upper()} yet. "
            f"{UNSETTLED_CHARGE_EXPONENT[code]} The invoice itself is "
            f"unaffected — you can still send it and record payment by hand."
        )


def _stripe_exponent(currency):
    """How many decimal places Stripe uses for this currency.

    Only reached for currencies `guard_chargeable` has allowed, which are the
    ones where ISO 4217 and Stripe agree.
    """
    return decimals_for(currency)


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
    return int(round(amount * (10 ** _stripe_exponent(currency))))


def from_minor_units(amount, currency):
    """Convert an integer Stripe amount back to a decimal. The inverse of
    ``to_minor_units``, and it has to exist for the same reason.

    THIS SIDE WAS MISSED WHEN THE OTHER SIDE WAS FIXED, and missing it was
    worse than leaving both wrong. Before ``to_minor_units``, the webhook's
    ``amount_total / 100`` was paired with an outbound ``amount * 100``, and
    for a zero-decimal currency the two errors CANCELLED: a ¥1,500 invoice was
    sent as 150000, the client was overcharged ¥150,000 -- and the webhook read
    150000 back, divided by 100, and recorded the correct ¥1,500. The books
    looked right while the card was wrong.

    Fixing only the outbound half un-cancelled the pair. Stripe then charged
    the correct ¥1,500, the webhook read 1500 back, divided by 100, and
    recorded **¥15** against a ¥1,500 invoice -- which never settles, chases
    the client forever, and is a worse failure than the overcharge because
    nothing about it looks wrong.

    Caught by Codex on PR #289 before this merged, and by
    tests/test_stripe_minor_units.py now.
    """
    digits = _stripe_exponent(currency)
    return round(amount / (10 ** digits), digits)


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
    # Before anything is sent: refuse a currency whose charge exponent we
    # cannot be certain of, rather than mischarge by a factor of a hundred.
    guard_chargeable(currency)
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
