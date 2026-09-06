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

from currencies import decimals_for, get_currency

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
    """True when this adapter can convert the amount with confidence.

    THIS IS A QUESTION ABOUT ARITHMETIC, NOT ABOUT STRIPE'S CATALOGUE. It
    answers "do we know how many minor units this amount is", which is the
    question that stops a 100x mischarge. It does NOT assert that Stripe will
    present the currency: KPW, CUP and IRR are ordinary two-decimal ISO codes
    and Stripe will not take any of them.

    That gap is real and is deliberately not closed by a second hard-coded
    list. Stripe's supported-presentment list is not reachable from this
    environment, and writing one from memory is precisely what put HUF on the
    divergent list on a misreading. The residue is handled where the truth
    actually lives instead: `create_checkout_session` turns Stripe's own
    rejection into the same readable refusal, so the failure is legible rather
    than a raw API error, and nobody is ever charged the wrong amount — a
    currency Stripe will not present cannot be charged at all.

    Raised by Codex on PR #289, round five.

    THE CODE MUST BE ONE WE KNOW. `decimals_for` answers 2 for anything it has
    never heard of, which is a sensible display fallback and a terrible basis
    for a charge: it made every unrecognised code chargeable, so the allowlist
    was quietly guessing that an unknown currency uses Stripe's default -- the
    exact thing it exists to stop. The JSON API takes a free-text currency, so
    this was reachable.
    """
    code = (currency or "usd").lower()
    if get_currency(code) is None:
        return False
    return decimals_for(code) == 2 and code not in DIVERGENT_FROM_ISO


def why_not_chargeable(currency):
    """The reason, in words the owner can act on."""
    code = (currency or "usd").lower()
    if code in DIVERGENT_FROM_ISO:
        return (
            f"Stripe handles {code.upper()} differently from the international "
            "standard, and exactly how could not be confirmed."
        )
    if get_currency(code) is None:
        return (
            f"{code.upper()} is not a currency code we recognise, so we cannot "
            "tell how Stripe would interpret the amount."
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


def configure(secret_key):
    stripe.api_key = secret_key


# --------------------------------------------------------------------------
# Connect onboarding (Standard)
# --------------------------------------------------------------------------
#
# THESE FOUR WERE DELETED BY ACCIDENT ON THIS BRANCH and restored on 6 Sep
# 2026. Rewriting the head of this module to carry the currency allowlist took
# `configure`, `create_connect_account`, `create_account_link`, `get_account`
# and `_platform_fee_cents` out with it. `app.py` calls every one of them, so
# connecting a Stripe account and creating a payment session both raised
# NameError — the entire payment feature was dead — and the suite stayed green
# for three commits, because nothing exercises a function whose body is a
# network call.
#
# tests/test_stripe_surface.py now asserts that every attribute the app
# reaches for on this module exists. That test is the point of this incident:
# a deletion is invisible to a suite that only tests what it can call.
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
    try:
        session = stripe.checkout.Session.create(
            **params, stripe_account=connected_account_id
        )
    except stripe.InvalidRequestError as exc:
        # STRIPE IS THE AUTHORITY ON WHICH CURRENCIES IT WILL PRESENT, and
        # `is_chargeable` deliberately does not try to be (see its docstring).
        # A code it will not take reaches here and comes back as a rejection;
        # left alone the client saw "Stripe error: Invalid currency: kpw",
        # which reads like our software broke. Same words as every other
        # refusal, so the owner knows what to do next.
        if "currency" in str(exc).lower():
            raise UnsupportedCurrency(
                f"Stripe will not take a payment in {currency.upper()}. "
                f"The invoice itself is unaffected — you can still send it "
                f"and record payment by hand. (Stripe said: {exc})"
            ) from exc
        raise
    return session


def construct_webhook_event(payload, sig_header, webhook_secret):
    """Verify and parse an incoming Stripe webhook payload."""
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
