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

#: WHICH CURRENCIES THIS ADAPTER WILL CHARGE IN -- an ALLOWLIST, deliberately.
#:
#: The previous version was a denylist of four currencies I had noticed were
#: disputed, which quietly assumed I had found them all. Three review rounds
#: proved I had not: HUF was added to it on a misreading (its zero-decimal rule
#: is documented for PAYOUTS, not charges) and ISK was missing entirely. For a
#: number that goes on somebody's card, "allow unless known bad" is the wrong
#: polarity. The firm chose this shape on 6 September 2026.
#:
#: THE RULE, and the evidence for it:
#:
#:   ALLOWED -- a currency ISO 4217 gives two decimal places, which is Stripe's
#:   default and the arithmetic this app has always used for them. About 130 of
#:   the 157, including every currency Invoicer offered before the picker
#:   existed bar one.
#:
#:   REFUSED -- everything else, and each for a stated reason:
#:     * HUF, MGA, TWD  ISO gives 2, but currencies.py records Stripe departing
#:                      from it. The nature of the departure is exactly what
#:                      could not be pinned down.
#:     * zero-decimal   JPY, KRW, VND, CLP and the rest. Stripe very likely
#:                      agrees with ISO on these -- but ISK is ISO zero-decimal
#:                      and is reported to need 150000 for 1,500, which proves
#:                      the class HAS exceptions. Since I cannot enumerate
#:                      them, I cannot clear the class. Note that this app has
#:                      never charged JPY correctly, so there is no history to
#:                      lean on either.
#:     * three-decimal  KWD, BHD, OMR and the rest. Stripe applies its own
#:                      rounding to these and I could not confirm what.
#:
#: `docs.stripe.com` is not reachable from this environment, which is why none
#: of the above could be settled against the primary source. Inferring an
#: exponent from prose in a code comment is what produced the HUF error.
#:
#: WHAT A REFUSAL COSTS, and why it is the cheap side of the trade: an invoice
#: can still be RAISED, printed, emailed and marked paid by hand in any of the
#: 157. Only the "pay online" button is withheld. A refusal the owner can read
#: is recoverable in a minute; a silent 100x mischarge on a client's card is
#: not, and is invisible in our own books because the inbound decode applies
#: the same wrong rule and reads the right number back.
#:
#: TO WIDEN IT: confirm the currency's charge exponent against Stripe's own
#: documentation, add it to a charge-exponent table with the citation, and it
#: becomes chargeable. This list is meant to grow with evidence, not with
#: confidence.
DIVERGENT_FROM_ISO = ("huf", "mga", "twd")


class UnsupportedCurrency(RuntimeError):
    """Raised rather than charge an amount we cannot be sure of."""


def is_chargeable(currency):
    """True when this adapter can convert the amount with confidence."""
    code = (currency or "usd").lower()
    return decimals_for(code) == 2 and code not in DIVERGENT_FROM_ISO


def why_not_chargeable(currency):
    """The reason, in words the owner can act on."""
    code = (currency or "usd").lower()
    if code in DIVERGENT_FROM_ISO:
        return (
            f"Stripe handles {code.upper()} differently from the international "
            "standard, and exactly how could not be confirmed."
        )
    places = decimals_for(code)
    if places == 0:
        return (
            f"{code.upper()} has no decimal places, and Stripe's handling of "
            "those has exceptions we have not been able to confirm."
        )
    if places == 3:
        return (
            f"{code.upper()} has three decimal places, and Stripe applies its "
            "own rounding to those which we have not been able to confirm."
        )
    return f"{code.upper()} is not a currency we can take payment in yet."


def guard_chargeable(currency):
    """Refuse a currency this adapter cannot convert with confidence."""
    if is_chargeable(currency):
        return
    code = (currency or "usd").lower()
    raise UnsupportedCurrency(
        f"Online payment is not available for {code.upper()} yet. "
        f"{why_not_chargeable(code)} The invoice itself is unaffected — you "
        f"can still send it and record payment by hand."
    )


def _stripe_exponent(currency):
    """How many decimal places Stripe uses for this currency.

    Only ever reached for a currency `guard_chargeable` has allowed, and every
    one of those is two-decimal in ISO 4217 with no known Stripe departure --
    so ISO's answer is Stripe's answer. The indirection stays because the day
    a verified exponent table arrives, this is the one place it plugs in.
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
