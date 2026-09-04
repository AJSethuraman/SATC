"""A bill a client can actually pay, and a way to know that they did.

THE INVOICE PROMISED A LINK IT DID NOT CARRY. `firm-settings.yaml` has told
every client since August that "Payment is by card or bank transfer through the
secure Square link on your invoice", and the invoice carried forty-one merge
fields, not one of them a URL. The client was told to click something that was
not on the page.

AND NOTHING RECORDED THAT ANYBODY HAD PAID. Every engagement letter says "We
will not e-file a return before the invoice for it is settled, unless agreed
upon in writing" -- a promise in writing, on a fact the software could not see.
`signing.may_file` had to report it as unknown, which is the honest answer and
not a useful one.

A LINK BELONGS TO A BILL, NEVER TO A QUOTE. The firm, 30 August 2026: *"Quotes
get no link. Only the invoice. Obviously."* An estimate is what work will cost
and is not yet owed; a link on one invites a client to pay a number that can
still move -- and this engine can now re-quote, so it does move. `PaymentUrl` is
declared for the invoice template alone and a test holds that line.

THE PROCESSOR IS A SETTING. Measured over the firm's own fee schedule, the
spread between processors is small and the spread between card and bank transfer
is not; the firm chose Square having seen the figures. `Processor` is the
interface, `Square` is the implementation, and nothing else in this software
knows which one is running.

WHY urllib AND NOT `requests`. `client-documents/requests.py` is this project's
own module -- the document request list -- and it SHADOWS the HTTP library
inside this package: `import requests` here returns the wrong thing entirely.
The standard library has no such problem and adds no dependency to declare.

NOTHING HERE HOLDS A CREDENTIAL, AND NOTHING IN THE REPOSITORY DOES. The token
is resolved at the moment of a call -- `$SATC_SQUARE_TOKEN` first, then a token
the owner chose to remember, which lives OUTSIDE the repository in their own
profile, sealed with DPAPI so no other Windows account can read it. It is never
logged, echoed in an error, or written to any engagement file. Tests assert that.

The remembered token exists because "set an environment variable in the shell
that runs this" is an obstacle in front of a credential, and an obstacle in
front of a credential is how the credential ends up somewhere worse -- pasted
into a file, or into a note. `payments --setup` asks once per account.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Callable

CONFIRM = re.compile(r"\[CONFIRM:\s*(.*?)\s*\]", re.S)
_TOKEN = re.compile(r"<<(\w+)>>")

# THE STATES OBSERVED, and the reason no state is trusted on its own.
#
# Against the live sandbox, 2-3 September 2026, one quick-pay link went:
#   DRAFT      made, nobody has been near it
#   OPEN       a card was charged; Square's panel reported "Your test payment
#              was successful" and "Tender.id: Added to Order" in the same breath
# `COMPLETED` never appeared. This constant was written from the API docs, and
# twice in two days a comment here asserted a state's meaning from one reading
# rather than from a reply -- first that an unpaid link reads `OPEN` (it reads
# `DRAFT`), then that `OPEN` is a state this flow does not produce (it is the
# state a PAID link sits in).
#
# So the answer is not a better guess at the vocabulary. `Settlement.paid` asks
# whether a TENDER exists -- whether somebody's card was actually charged --
# and treats `COMPLETED` as sufficient but not necessary. A label can be
# renamed by the processor; money changing hands cannot.
PAID = "COMPLETED"


class PaymentError(RuntimeError):
    """Something that would put a wrong link, or a wrong figure, on a bill.

    IT CARRIES THE STATUS when the processor gave one. A caller that wants to
    react to an AUTHORIZATION refusal specifically -- and only `live_check`
    does -- would otherwise have to match on the wording of a message written
    for a person to read, which breaks the moment the wording improves.
    """

    def __init__(self, message: str, code: int | None = None,
                 fact: str = ""):
        super().__init__(message)
        self.code = code
        # THE SAME REFUSAL, WITHOUT THE GUESSING. `live_check` finds out which
        # cause it is and must print its finding INSTEAD of the possibilities,
        # not after them -- a paragraph of hypotheses above the answer argues
        # against the answer.
        self.fact = fact or message


@dataclass(frozen=True)
class Link:
    """A thing a client can pay, as the processor issued it."""
    id: str
    order_id: str
    url: str
    amount_cents: int
    invoice: str
    created: str

    def as_record(self) -> dict:
        """What the invoice file keeps. `PaymentUrl` is the merge field; the
        rest is bookkeeping and is `_`-prefixed so it cannot reach a document."""
        return {
            # THE FLAG IS SEPARATE FROM THE VALUE. A condition is a flag and a
            # value is a field; using the URL as its own condition registers
            # one name as two things, and the registry check says so.
            "PaymentLink": True,
            "PaymentUrl": self.url,
            "_payment": {"processor": "square", "link_id": self.id,
                         "order_id": self.order_id, "amount": self.amount_cents,
                         "created": self.created},
        }


@dataclass(frozen=True)
class Settlement:
    """What the processor says about one order.

    TWO FIGURES, BECAUSE THEY CAN DISAGREE. `amount_cents` is what the order
    was FOR; `tendered_cents` is what was actually handed over, summed off the
    order's tenders. On an ordinary quick-pay link they are the same number and
    the distinction is idle. They come apart on a partial tender -- and a bill
    is only covered by what arrived, never by what was asked.
    """
    order_id: str
    state: str
    amount_cents: int = 0
    when: str = ""
    tendered_cents: int = 0

    @property
    def paid(self) -> bool:
        """Did money actually come in.

        A TENDER IS MONEY; A STATE IS A LABEL. This asked only whether the
        order read `COMPLETED`, and the firm's own paid sandbox link came back
        `OPEN` with a tender on it -- Square's testing panel said, in order,
        "Your test payment was successful", "Tender.id: Added to Order",
        "Order state: OPEN". So a bill the firm HAD been paid for would have
        been reported unpaid, for ever, and `signing.may_file` would have gone
        on refusing to clear a return whose invoice was settled.

        `COMPLETED` still counts on its own, because an order can be closed
        without this seeing its tenders. But a tender is the thing that means
        somebody's card was charged, and it is now enough by itself.

        THIS IS NOT A LOOSENING. Settling a bill takes more than money
        arriving: `record_settlement` compares what arrived to what was owed
        and refuses to settle a short payment. This says money came in; that
        says whether it covered the bill.
        """
        return self.state == PAID or self.tendered_cents > 0

    @property
    def arrived_cents(self) -> int:
        """What the firm actually got. The tenders when the processor reports
        them, the order total when it does not -- never a guess of zero."""
        return self.tendered_cents or self.amount_cents


@lru_cache(maxsize=1)
def settings() -> dict:
    path = Path(__file__).resolve().parent / "registry" / "payments.yaml"
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def unwritten(reg: dict | None = None) -> list[str]:
    """Every `[CONFIRM: ]` still standing in the payments registry.

    Reported rather than raised, so a caller can say what is waiting on the firm
    without a traceback -- the same way `pricing.open_amounts` does.
    """
    reg = reg if reg is not None else settings()
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, str) and CONFIRM.search(node):
            out.append(path)

    walk(reg, "")
    return sorted(out)


def _location_key(sandbox: bool) -> str:
    """Which location id a run uses. Stated once; both callers ask here."""
    return "sandbox_location_id" if sandbox else "location_id"


def _unused_location(sandbox: bool) -> str:
    """The other one -- not waiting on the firm, just not this run's."""
    return _location_key(not sandbox)


def _fill(text: str, record: dict) -> str:
    missing = [n for n in _TOKEN.findall(text or "")
               if not str(record.get(n, "")).strip()]
    if missing:
        raise PaymentError(
            f"the payment link's name needs {', '.join(sorted(set(missing)))}, "
            f"which this invoice has no value for. It is what the client sees "
            f"on Square's page and on their card statement."
        )
    return _TOKEN.sub(lambda m: str(record.get(m.group(1), "")), text or "")


def _cents(amount) -> int:
    """A money string or number -> integer cents. Never a float.

    `money.parse` returns a float and Square takes an integer of the smallest
    unit. Rounding at this boundary, in one place, is why the invoice that
    billed $275.08 could not become 27507.
    """
    import money as m

    value = m.parse(amount)
    if value is None:
        raise PaymentError(
            f"{amount!r} is not an amount a link can be made for. An invoice "
            f"carrying a `[CONFIRM:` has no figure to charge, and a link for "
            f"nothing is worse than no link."
        )
    if value <= 0:
        raise PaymentError(
            f"a payment link for {amount} would ask a client to pay nothing. "
            f"An invoice that owes nothing needs no link."
        )
    return int(round(value * 100))


# ── the seam ──────────────────────────────────────────────────────────────

class Square:
    """Square's Checkout and Orders APIs, over four fields and two calls.

    `transport` is the seam: a callable taking (method, url, headers, body) and
    returning the decoded response. Tests pass a stub, so every rule in here --
    the idempotency key, the cents, the error a refusal produces -- is exercised
    without a network. The real one is `_http` below.
    """

    name = "square"

    def __init__(self, *, token: str, location_id: str, host: str,
                 version: str, transport: Callable | None = None,
                 sandbox: bool = False):
        self.token = token
        self.location_id = location_id
        self.host = host
        self.version = version
        # WHICH ACCOUNT THIS IS, carried rather than re-derived. `link_for`
        # has to know which of the two location ids it is allowed to still be
        # waiting on, and comparing `host` against the registry to find out
        # would be a second statement of a rule already stated here.
        self.sandbox = sandbox
        self._send = transport or _http

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        return self._send(method, f"https://{self.host}{path}", {
            "Authorization": f"Bearer {self.token}",
            "Square-Version": self.version,
            "Content-Type": "application/json",
        }, body)

    def create_link(self, *, invoice: str, amount_cents: int, name: str,
                    today: date | None = None) -> Link:
        """One payment link for one invoice.

        THE IDEMPOTENCY KEY IS THE INVOICE NUMBER, which is the whole point of
        it: running `invoice` twice must not leave two live links against one
        bill, each able to take the money. Square returns the original link for
        a repeated key rather than making a second.
        """
        # NOTHING UNFILLED REACHES A PAYER. `_fill` already refused an
        # unresolved token, and `live_check` was then written with its own,
        # worse way of preparing the same string -- so a real sandbox checkout
        # page went up reading `SATC <<InvoiceNumber>>`, to a person about to
        # type a card number into it. The guard belongs at the boundary every
        # caller passes, not in one of the two functions that build a name.
        if _TOKEN.search(name or ""):
            raise PaymentError(
                f"the payment link's name still has "
                f"{', '.join(sorted(set(_TOKEN.findall(name))))} in it, "
                f"unfilled. That is the line a client reads on Square's page "
                f"and on their card statement. No link has been made."
            )
        got = self._call("POST", "/v2/online-checkout/payment-links", {
            "idempotency_key": f"satc-{invoice}",
            "quick_pay": {
                "name": name,
                "price_money": {"amount": amount_cents, "currency":
                                settings().get("currency", "USD")},
                "location_id": self.location_id,
            },
            "payment_note": invoice,
        })
        link = (got or {}).get("payment_link") or {}
        if not link.get("url") or not link.get("order_id"):
            raise PaymentError(
                "Square accepted the request and returned no link. Nothing has "
                "been put on the invoice; the bill is unchanged."
            )
        return Link(id=link.get("id", ""), order_id=link["order_id"],
                    url=link["url"], amount_cents=amount_cents,
                    invoice=invoice,
                    created=(today or date.today()).isoformat())

    def settled(self, order_ids: list[str]) -> dict[str, Settlement]:
        """What the processor says about these orders. Polled, not pushed.

        A WEBHOOK WOULD NEED A SERVER THIS FIRM DOES NOT HAVE. Polling asks the
        question when somebody wants the answer, from a laptop, with nothing
        listening on the internet. Square takes up to a hundred ids per call.
        """
        out: dict[str, Settlement] = {}
        for chunk in [order_ids[i:i + 100] for i in range(0, len(order_ids), 100)]:
            got = self._call("POST", "/v2/orders/batch-retrieve",
                             {"order_ids": chunk})
            for order in (got or {}).get("orders") or []:
                oid = order.get("id", "")
                out[oid] = Settlement(
                    order_id=oid,
                    state=order.get("state", ""),
                    amount_cents=((order.get("total_money") or {})
                                  .get("amount") or 0),
                    when=(order.get("closed_at") or "")[:10],
                    tendered_cents=sum(
                        (t.get("amount_money") or {}).get("amount") or 0
                        for t in (order.get("tenders") or [])),
                )
        return out

    def locations(self) -> list[dict]:
        """Every location this token can see. The cheapest real question.

        It is the only call that proves the TOKEN is good and the LOCATION ID
        is one of the firm's own, and it moves no money to ask. A typo in the
        location id is otherwise invisible until a client is standing at a
        checkout page that will not load.
        """
        return (self._call("GET", "/v2/locations") or {}).get("locations") or []

    def deactivate(self, link: Link) -> None:
        """Take a link out of service. Used when a bill is re-quoted.

        A LINK OUTLIVING ITS FIGURE IS THE ONE WAY THIS FEATURE TAKES THE WRONG
        AMOUNT. Re-price an engagement from $645 to $745 and the old link will
        still cheerfully collect $645.
        """
        self._call("DELETE", f"/v2/online-checkout/payment-links/{link.id}")


def _refusal(code: int, detail: str, url: str) -> str:
    """What to say when the processor refuses, to a caller that cannot ask more.

    THE FACT AND THE GUESSING ARE SEPARATE, because one caller can do better
    than guess. `link_for` and everything else that talks to the processor get
    both halves: the refusal, then the possible causes. `live_check` takes the
    fact alone and prints what it FOUND OUT in place of the possibilities --
    a paragraph of hypotheses above an answer argues against the answer, and
    for a while this printed both, ninety-three words to say forty-five.
    """
    return _fact(code, detail) + _guesses(code, url)


def _fact(code: int, detail: str) -> str:
    """What happened, with nothing added.

    Square's own sentence already ends in a full stop, so this does not add a
    second one -- a real run printed `authorized..` before it did that.
    """
    said = (detail or "").strip()
    out = f"the payment processor refused: {code}"
    if said:
        out += f" — {said.rstrip('.')}"
    return out + ". Nothing has been put on the invoice."


def _guesses(code: int, url: str) -> str:
    """The possible causes of a refusal, for a caller that cannot find out which.

    WHAT ONE REFUSAL CAN AND CANNOT TELL YOU. This once named a token from the
    other tab as "the commonest cause", and then a real run refused the SAME
    token on BOTH hosts -- so on each of the two runs the message confidently
    named the one place the problem was not, contradicting itself between them.
    A single 401 distinguishes none of these, so this lists them and chooses
    none. Tenet 1, in the code that quotes tenet 1.

    Only an authorization refusal gets this. A rate limit or a server fault has
    nothing to do with the token, and sending somebody to re-copy one would
    send them the wrong way.
    """
    if code not in (401, 403):
        return ""
    # THE CONSOLE'S OWN WORDS, not ours. Square labels the two tabs "Sandbox"
    # and "Production"; telling somebody to look for a "live" tab sends them
    # hunting for a thing that is not on the screen in front of them.
    where = "Sandbox" if "squareupsandbox" in url else "Production"
    other = "Production" if where == "Sandbox" else "Sandbox"
    return (
        f" Square did not accept the token. This run used the {where} account, "
        f"so it may be the {other} one, or not an access token at all — the "
        f"application id and the application secret sit on the same console "
        f"page, and a token can be revoked. `payments --check` asks both "
        f"accounts and says which."
    )


def _http(method: str, url: str, headers: dict, body: dict | None) -> dict:
    """One HTTP call, on the standard library.

    Errors are re-raised WITHOUT the request, because the request carries the
    Authorization header and an exception string ends up in a terminal, a log
    and whatever screenshot gets pasted into a ticket.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers,
                                     method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as answer:
            raw = answer.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            problem = json.loads(exc.read().decode("utf-8"))
            detail = "; ".join(e.get("detail", "") for e in
                               (problem.get("errors") or []))
        except Exception:                                  # noqa: BLE001
            pass
        raise PaymentError(_refusal(exc.code, detail, url), code=exc.code,
                           fact=_fact(exc.code, detail)) from None
    except urllib.error.URLError as exc:
        raise PaymentError(
            f"the payment processor could not be reached ({exc.reason}). The "
            f"invoice is unchanged; try again when the network is back."
        ) from None
    return json.loads(raw) if raw else {}


def _remembered(sandbox: bool) -> str:
    """A token sealed into the user's profile by `payments --setup`, or "".

    THE ENVIRONMENT STILL WINS where it is set. This is the fallback that means
    the firm answers "what is your token" ONCE per account rather than in every
    shell it ever invoices from -- and an obstacle in front of a credential is
    how the credential ends up pasted somewhere worse.

    Imported lazily: `square_setup` is a front-door convenience and nothing in
    the payment path should fail to import because of it.
    """
    try:
        import square_setup
        return square_setup.stored_token(sandbox)
    except Exception:            # noqa: BLE001 -- absent or unreadable is ""
        return ""


class LinkChoice:
    """Whether this run may create a live payment link, and the reason.

    `wanted` is the answer; `reason` is what to print. A suppression that
    happens silently is the same bug in a quieter form -- somebody re-runs the
    command wondering where the link went.
    """

    __slots__ = ("wanted", "reason")

    def __init__(self, wanted: bool, reason: str) -> None:
        self.wanted, self.reason = wanted, reason

    def __repr__(self) -> str:                        # for test failures
        return f"LinkChoice(wanted={self.wanted!r}, reason={self.reason!r})"


def link_follows_the_store(*, store, default_store, no_link: bool = False,
                           link: bool = False) -> LinkChoice:
    """THE MONEY SEAM IS SCOPED BY `--store`, THE SAME WAY THE FILES ARE.

    Until 4 September 2026 it was not. `--store` routed where the invoice JSON
    was written; the processor and its token came from `registry/payments.yaml`
    and the Windows credential store, so **a run scoped entirely to a scratch
    directory still reached the firm's production Square account.** The
    standing instruction on the machine this runs on is *point tests at a temp
    store*; an agent obeying it believed it was isolated and was not.

    It was caught by an assessment agent doing exactly that, which got back
    `400 -- This idempotency key has already been used to create a Payment
    Link` and therefore created nothing. **A 400 is not the reassurance it
    looks like.** 400 is what a *differing body* returns. The key is
    `satc-<invoice>` while the invoice number is scanned from the local store
    only, so a fresh temp store starts at `2026-0001` and collides with keys
    already spent on the live account -- and had the amount matched, Square
    returns the EXISTING link. A fictional test client would have been handed a
    real client's payment link.

    So the default now follows the store, and the firm chose it that way:
    *"--no-link defaults on any non-default --store"*, 4 September 2026.

    Precedence, most explicit first:

    - `--no-link` -- never, whatever the store. An explicit refusal.
    - `--link` -- yes, whatever the store. **This is the escape hatch**, and it
      has to exist: without it a firm that keeps its engagements somewhere other
      than the default could never raise a real bill.
    - otherwise -- the default store gets a link, any other store does not.

    Both flags together is a contradiction rather than a precedence puzzle, and
    is refused rather than silently resolved.
    """
    if no_link and link:
        raise PaymentError(
            "--link and --no-link ask for opposite things. Pass one.")
    if no_link:
        return LinkChoice(False, "no link: --no-link was passed")
    if link:
        return LinkChoice(True, "")
    # `resolve()` on both sides: `engagements/.` and `engagements` are the same
    # directory, and a comparison that says otherwise suppresses a link the
    # firm asked for.
    same = Path(store).resolve() == Path(default_store).resolve()
    if same:
        return LinkChoice(True, "")
    return LinkChoice(False,
                      f"no link: this run is scoped to {Path(store)}, which is "
                      f"not the engagement store, so it does not touch live "
                      f"payments. Pass --link if you meant to bill for real.")


def processor(*, sandbox: bool = False, transport: Callable | None = None,
              reg: dict | None = None, token: str | None = None) -> Square:
    """The configured processor, or a refusal saying what is missing.

    `token` is for the one caller that HAS a token and has not stored it yet:
    setup, holding what was just typed, deciding whether it works before
    sealing it. Everywhere else leaves it None and the environment or the
    remembered token answers.
    """
    reg = reg if reg is not None else settings()
    which = reg.get("processor", "")
    if which != "square":
        raise PaymentError(
            f"`registry/payments.yaml` selects the processor {which!r}, and "
            f"only `square` is implemented. The seam is there; the adapter is "
            f"not written."
        )
    conf = reg.get("square") or {}
    waiting = [p for p in unwritten(reg) if p.startswith("square.")
               and p != f"square.{_unused_location(sandbox)}"]
    if waiting:
        raise PaymentError(
            "the payments registry is not filled in yet — "
            + ", ".join(waiting) + " is still a `[CONFIRM: ]`."
        )
    env = conf.get("token_env") or "SATC_SQUARE_TOKEN"
    token = (token or "").strip() or os.environ.get(env, "").strip() \
        or _remembered(sandbox)
    if not token:
        raise PaymentError(
            f"no payment token. Run `python cli.py payments --setup` once and "
            f"it will ask for both, or set ${env} in this shell. A token is "
            f"never written into the repository — one in the repository is one "
            f"in every clone, backup and screenshot."
        )
    return Square(token=token, sandbox=sandbox,
                  location_id=conf.get(_location_key(sandbox), ""),
                  host=conf.get("sandbox_host" if sandbox else "api_host", ""),
                  version=conf.get("api_version", ""), transport=transport)


# ── what a caller actually does ───────────────────────────────────────────

def link_for(invoice_fields: dict, *, using: Square,
             reg: dict | None = None, today: date | None = None) -> Link:
    """A link for one invoice, named the way the firm names it."""
    reg = reg if reg is not None else settings()
    # EVERY unwritten field, not just the wording. This checked `link_name`
    # alone, and that was load-bearing by accident: while the copy carried a
    # `[CONFIRM:` nothing could get past it, so the placeholder `location_id`
    # was never reached. The firm approved the wording on 30 Aug 2026 and the
    # guard fell open -- link_for would have called Square carrying
    # "[CONFIRM: the location id from Square's developer console]" as a
    # location. Found because a test that named the OLD reason stopped firing.
    #
    # `unwritten()` walks the whole registry, so a field added later is covered
    # without anyone remembering to come back here. ONE EXCEPTION, and it is
    # narrow: there are two location ids and a run uses one of them, so the
    # other is not waiting on the firm -- it is waiting on a different run.
    waiting = [w for w in unwritten(reg)
               if w != f"square.{_unused_location(using.sandbox)}"]
    if waiting:
        raise PaymentError(
            "no payment link can be made yet — waiting on the firm for "
            + ", ".join(f"`{w}`" for w in waiting)
            + " in `registry/payments.yaml`."
        )
    name = str(reg.get("link_name", ""))
    number = str(invoice_fields.get("InvoiceNumber", "")).strip()
    if not number:
        raise PaymentError(
            "this invoice has no number, so a link could not be told apart "
            "from the next one — the number is the idempotency key."
        )
    return using.create_link(
        invoice=number,
        amount_cents=_cents(invoice_fields.get("AmountDue")),
        name=_fill(name, invoice_fields), today=today)


def outstanding(store: Path) -> list[dict]:
    """Every invoice with a link and no settlement, oldest first."""
    import invoicing

    out = []
    for folder in sorted(Path(store).glob("*/invoices")):
        for path in sorted(folder.glob("*.json")):
            try:
                bill = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            pay = bill.get("_payment") or {}
            if pay.get("order_id") and not bill.get("SettledOn"):
                out.append({"path": path, "ref": folder.parent.name,
                            "invoice": bill.get("InvoiceNumber", ""),
                            "order_id": pay["order_id"],
                            "amount": bill.get("AmountDue", "")})
    return out


@dataclass(frozen=True)
class Posting:
    """What happened when one processor answer met one bill.

    `settled` is the only thing the old return value said, and it is still the
    thing most callers want. `problem` is why a payment that ARRIVED did not
    settle its bill -- empty when there is nothing to say.
    """
    settled: bool = False
    due_cents: int = 0
    arrived_cents: int = 0
    problem: str = ""

    @property
    def short(self) -> bool:
        """Money came in and did not cover the bill."""
        return bool(self.arrived_cents) and self.arrived_cents < self.due_cents


def _due_cents(bill: dict) -> int:
    """What this bill says is owed, in cents. Raises if it cannot be read."""
    return _cents(bill.get("AmountDue"))


def record_settlement(path: Path, got: Settlement) -> Posting:
    """Write a settlement onto its invoice. Says what moved, and what did not.

    THE PROCESSOR IS THE SYSTEM OF RECORD FOR MONEY, and this is a cache of its
    answer -- which is why it is written onto the bill rather than into an
    append-only log. What must never be cached is a NEGATIVE: an unpaid order
    is simply left alone, so nothing here can mark a bill unpaid that the
    processor has since settled.

    A PAYMENT IS NOT A SETTLEMENT UNTIL THE FIGURES MATCH. `deactivate` exists
    because a link outlives its figure: re-price an engagement from $645 to
    $745 and the old link still cheerfully collects $645. That was written down
    as the one way this feature takes the wrong amount, and then nothing
    downstream ever compared the two numbers -- `settled_amount` was written
    onto every bill and read by nobody. So a client could pay $645 against a
    $745 bill, the bill would be marked settled, and `signing.may_file` would
    open the e-file gate that every engagement letter promises stays shut until
    the invoice is settled. A short payment now leaves `SettledOn` unwritten:
    the gate stays shut by construction rather than by a report somebody reads.

    An OVERpayment settles -- the bill is covered and holding a return hostage
    over the firm's own refund would be absurd -- but it is written down and
    said out loud, because somebody owes the client money back.
    """
    if not got.paid:
        return Posting()
    bill = json.loads(Path(path).read_text(encoding="utf-8"))
    if bill.get("SettledOn"):
        return Posting()

    arrived = got.arrived_cents
    try:
        due = _due_cents(bill)
    except PaymentError:
        # A bill whose figure cannot be read cannot be checked against the money
        # that arrived, and settling it would be settling against nothing.
        return Posting(arrived_cents=arrived, problem=(
            f"{arrived / 100:,.2f} arrived against invoice "
            f"{bill.get('InvoiceNumber', '')}, whose amount due is not a figure "
            f"this software can read. Nothing has been marked settled."))

    if arrived < due:
        bill["_payment"] = {**(bill.get("_payment") or {}), "state": got.state,
                            "settled_amount": arrived, "due_amount": due,
                            "short_by": due - arrived}
        Path(path).write_text(
            json.dumps(bill, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        return Posting(due_cents=due, arrived_cents=arrived, problem=(
            f"${arrived / 100:,.2f} arrived against a bill for "
            f"${due / 100:,.2f} — ${(due - arrived) / 100:,.2f} short. The "
            f"invoice is NOT settled and the return is not clear to file. "
            f"A link made before a re-quote collects the old figure; check "
            f"whether this bill was re-priced after its link went out."))

    bill["SettledOn"] = got.when or date.today().isoformat()
    bill["_payment"] = {**(bill.get("_payment") or {}), "state": got.state,
                        "settled_amount": arrived, "due_amount": due}
    over = arrived - due
    if over:
        bill["_payment"]["over_by"] = over
    Path(path).write_text(json.dumps(bill, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return Posting(settled=True, due_cents=due, arrived_cents=arrived,
                   problem=("" if not over else
                            f"${arrived / 100:,.2f} arrived against a bill for "
                            f"${due / 100:,.2f} — ${over / 100:,.2f} more than "
                            f"was owed. The bill is settled. Put the "
                            f"${over / 100:,.2f} on the next bill as a credit "
                            f"rather than refunding it: Square keeps the "
                            f"processing fee on a refund, so sending it back "
                            f"costs the firm the fee on money it never asked "
                            f"for. The next `invoice` on this engagement will "
                            f"remind you."))


# ── proving it works, against the real processor ──────────────────────────
#
# THE FIRM'S QUESTION, 2 September 2026: *"how do we truly confirm the square
# thing works - i want to know i'll get paid and the client isn't just sending
# money to the void"*.
#
# Every test in `tests/test_payments.py` runs against a fake transport. They
# prove this software sends the right request and reacts correctly to an
# answer. THEY PROVE NOTHING ABOUT SQUARE -- not that the token works, not that
# the location id is the firm's, not that a client can open the page. A green
# suite and a dead account look identical from here.
#
# So this walks the loop against the live API and says, step by step, what each
# step actually established -- and, just as importantly, what it did not.


@dataclass(frozen=True)
class Step:
    """One thing that was checked, and what checking it proved."""
    name: str
    ok: bool
    detail: str = ""


# NOT "SATC-CHECK-". The firm's `link_name` is `SATC <<InvoiceNumber>>`, so a
# number beginning `SATC-` renders as `SATC SATC-CHECK-2026-09-03` on the very
# line a payer reads on their card statement. The firm's name belongs to the
# name template; this is only the number.
CHECK_PREFIX = "CHECK-"

# HOW MANY STEPS THE LOOP HAS, stated once. `live_check` returns only the steps
# it REACHED, and a caller has to be able to say "3 of 7" rather than "3 of 3"
# -- the whole point of the report is the denominator. Counting them at the
# call site is the same bug this repository keeps finding: a claim in one place,
# the behaviour in another, and nothing comparing them. A test does the
# comparing.
CHECK_STEPS = 7


def check_number(today: date | None = None) -> str:
    """The scratch invoice number a live check bills itself against.

    STABLE WITHIN A DAY, ON PURPOSE. The idempotency key is the invoice number,
    so re-running the check on the same day returns the SAME link rather than
    a second one -- which is what makes "open it, pay it, run the check again"
    work without this having to store anything.
    """
    return CHECK_PREFIX + (today or date.today()).isoformat()


def _asks_the_other_account(reg: dict, sandbox: bool, transport) -> str:
    """Put the same token to the OTHER account, and say what the answer proves.

    THE REPORT THAT WAS WRONG BOTH WAYS. A run against Sandbox said the token
    was probably a Production one; the same token against Production said it
    was probably a Sandbox one. Both cannot be true, and between them they had
    already ruled out the thing each was asserting -- the observation needed
    was sitting one request away and nothing went and made it.

    `/v2/locations` is a read: it moves no money and creates nothing, which is
    why it is safe to make on a caller's behalf without asking. It is only
    made when the first account has already refused, so an ordinary run makes
    no extra call at all.
    """
    other = not sandbox
    conf = (reg or {}).get("square") or {}
    name = "Sandbox" if other else "Production"
    ran = "Production" if other else "Sandbox"
    try:
        # The location id is irrelevant to listing locations, and the other
        # account's is usually still a `[CONFIRM:`, so it is stubbed rather
        # than waited on -- this is a diagnosis, not a run against that account.
        elsewhere = processor(sandbox=other, transport=transport, reg={
            **reg, "square": {**conf, _location_key(other): "unknown"}})
        elsewhere.locations()
    except PaymentError as exc:
        if getattr(exc, "code", None) in (401, 403):
            # "Square did not accept the token" is what the line above this
            # already says. The finding is the second account, not the first.
            return (f" The {name} account refuses it too, so it is not a token "
                    f"for either account. Most likely it is the application id "
                    f"or the application secret rather than the ACCESS TOKEN; "
                    f"all three sit on the same console page. A revoked token "
                    f"does this too.")
        # Could not ask. Saying nothing is right: a guess dressed as a finding
        # is what this whole function exists to stop.
        return ""
    return (f" This is a {name} token and you ran {ran}. Use the {ran} access "
            f"token, or run the check against {name}.")


def _check_record(number: str) -> dict:
    """The fields a check's own link name is filled from.

    THE SAME `_fill` EVERY OTHER CALLER USES. This once did its own thing --
    `link_name.split("—")[0].strip()` -- on the assumption the firm's name was
    an em-dashed prefix. The registry says `SATC <<InvoiceNumber>>`, with no
    dash in it at all, so the split did nothing and the raw token went to
    Square. A real sandbox checkout page read `SATC <<InvoiceNumber>>` above a
    card field.

    Whatever the firm puts in `link_name`, it is filled from here or the check
    refuses rather than shipping a placeholder to a payer.
    """
    import settings as firm_settings

    out: dict = {}
    try:
        out.update({k: v for k, v in
                    (firm_settings.firm_fields(str(date.today().year)) or {}).items()
                    if isinstance(v, str) and v})
    except Exception:                                      # noqa: BLE001
        # A settings file that will not load is a real problem, and it is not
        # this function's to report -- `doctor` says so. `_fill` refuses here
        # rather than this guessing a firm name.
        pass
    # LAST, so nothing from the firm's settings can shadow it: the check bills
    # itself, and its number is the idempotency key that makes a re-run find
    # the same link instead of making a second one.
    out["InvoiceNumber"] = number
    return out


def live_check(*, sandbox: bool = True, amount_cents: int = 100,
               reg: dict | None = None, transport: Callable | None = None,
               today: date | None = None) -> tuple[list[Step], Link | None,
                                                   Settlement | None]:
    """Walk the whole payment loop against the real processor.

    Returns every step it took -- including the ones it could not take -- so a
    caller can report the DENOMINATOR. A check that quietly examined two things
    and printed a tick is worse than one that fails.

    It does not, and cannot, confirm the last mile: that the money reaches the
    firm's bank. Nothing short of one real payment and one real payout does.
    """
    reg = reg if reg is not None else settings()
    steps: list[Step] = []
    conf = (reg or {}).get("square") or {}
    which = _location_key(sandbox)
    env = conf.get("token_env") or "SATC_SQUARE_TOKEN"

    written = str(conf.get(which, ""))
    missing_location = not written or bool(CONFIRM.search(written))

    # THE TOKEN IS NEVER PRINTED, only whether one is there. An error message
    # ends up in a terminal, a log and whatever screenshot goes into a ticket.
    #
    # Asked the same way `processor` resolves it, or this reports "no token"
    # about a run that is about to work -- which is worse than a wrong answer,
    # because it sends someone looking for a problem that is not there.
    has_token = bool(os.environ.get(env, "").strip() or _remembered(sandbox))

    if missing_location and not has_token:
        steps.append(Step("the location id is written down", False,
                          f"`square.{which}` in registry/payments.yaml is still "
                          f"waiting on the firm, and no token is available, "
                          f"so this cannot look the id up for you either. Run "
                          f"`python cli.py payments --setup`."))
        return steps, None, None

    if missing_location:
        # THE CHICKEN AND THE EGG. Refusing to run until the location id is
        # written meant sending somebody into a web console to hunt for it --
        # and the firm came back with their APPLICATION id instead, which is a
        # different identifier entirely. The token can list the locations. So
        # ask, and print them, rather than asking a person to go and look.
        try:
            api = processor(sandbox=sandbox, reg={**reg, "square": {
                **conf, which: "unknown"}}, transport=transport)
            found = api.locations()
        except PaymentError as exc:
            more = (_asks_the_other_account(reg, sandbox, transport)
                    if getattr(exc, "code", None) in (401, 403) else "")
            said = f"{exc.fact}{more}" if more else str(exc)
            steps.append(Step("the location id is written down", False,
                              f"`square.{which}` is not filled in, and asking "
                              f"Square for it failed: {said}"))
            return steps, None, None
        steps.append(Step("the location id is written down", False,
                          f"`square.{which}` in registry/payments.yaml is "
                          f"still waiting on the firm. This token can see "
                          + (", ".join(f"{l.get('name', '(unnamed)')} = "
                                       f"{l.get('id')}" for l in found)
                             if found else "no locations at all")
                          + ". Put the id in the registry and run this again."))
        return steps, None, None

    steps.append(Step("the location id is written down", True, written))

    if not has_token:
        steps.append(Step("a token is available", False,
                          f"No token. Run `python cli.py payments --setup` "
                          f"once, or set ${env} in this shell."))
        return steps, None, None
    steps.append(Step("a token is available", True,
                      ("$" + env if os.environ.get(env, "").strip()
                       else "remembered on this Windows account")
                      + " (its value is not shown, here or anywhere else)"))

    try:
        api = processor(sandbox=sandbox, reg=reg, transport=transport)
    except PaymentError as exc:
        steps.append(Step("the processor can be built", False, str(exc)))
        return steps, None, None

    try:
        found = api.locations()
    except PaymentError as exc:
        more = (_asks_the_other_account(reg, sandbox, transport)
                if getattr(exc, "code", None) in (401, 403) else "")
        steps.append(Step("Square answers this token", False,
                          f"{exc.fact}{more}" if more else str(exc)))
        return steps, None, None
    steps.append(Step("Square answers this token", True,
                      f"{len(found)} location(s) on the account"))

    mine = next((loc for loc in found if loc.get("id") == api.location_id), None)
    if mine is None:
        steps.append(Step("the location id is one of yours", False,
                          f"{api.location_id} is not among the "
                          f"{len(found)} location(s) this token can see"
                          + (f" — those are: "
                             + ", ".join(f"{l.get('name', '?')} ({l.get('id')})"
                                         for l in found) if found else "")))
        return steps, None, None
    steps.append(Step("the location id is one of yours", True,
                      f"{mine.get('name', '(unnamed)')} — "
                      f"{mine.get('status', '?')}, "
                      f"{mine.get('currency', '?')}"))

    number = check_number(today)
    try:
        link = api.create_link(
            invoice=number, amount_cents=amount_cents,
            name=_fill(str(reg.get("link_name", "")) or "<<FirmName>>",
                       _check_record(number)),
            today=today)
    except PaymentError as exc:
        said = str(exc)
        if "idempotency" in said.lower():
            # THE KEY IS THE DAY, so a check link made earlier today cannot be
            # remade with different wording -- Square keeps the first one. It
            # is not a fault in the payment path and it clears at midnight; the
            # message used to leave somebody staring at a bare 400.
            said += (f" A check link was already made today, and Square keeps "
                     f"the first one for a given number. Nothing is wrong with "
                     f"the payment path — open the link from the earlier run, "
                     f"or run this again tomorrow.")
        steps.append(Step("a client can be given something to pay", False, said))
        return steps, None, None
    steps.append(Step("a client can be given something to pay", True,
                      f"a ${amount_cents / 100:,.2f} link at {link.url}"))

    try:
        got = api.settled([link.order_id]).get(link.order_id)
    except PaymentError as exc:
        steps.append(Step("the payment can be read back afterwards", False,
                          str(exc)))
        return steps, link, None
    if got is None:
        steps.append(Step("the payment can be read back afterwards", False,
                          f"Square made order {link.order_id} and then did not "
                          f"return it. A payment against it could not be seen."))
        return steps, link, None
    steps.append(Step("the payment can be read back afterwards", True,
                      f"order {link.order_id} reads `{got.state}`"
                      + (f", ${got.arrived_cents / 100:,.2f} in"
                         if got.paid else " — nobody has paid it yet")))

    steps.append(Step("the money arrived", got.paid,
                      f"${got.arrived_cents / 100:,.2f} settled {got.when}"
                      if got.paid else
                      "nothing has been paid against this link yet. Open it, "
                      "pay it, and run this again."))
    return steps, link, got


def unapplied_overpayments(store: Path, ref: str) -> list[dict]:
    """Money this engagement has paid over its bills and not yet been given back.

    THE FIRM, 2 September 2026, on being told an overpayment settles the bill:
    *"i am not eating a fee for them doing it... right?"*

    Right, and the way not to is to CREDIT it rather than refund it. Square
    stopped returning the processing fee on refunds to US sellers on 11 April
    2023 (squareup.com/us/en/press/policy-and-pricing-updates), so refunding
    $100 costs the firm the fee on $100 and recovers none of it. Carrying it
    onto the next bill costs nothing at all.

    Which only works if somebody REMEMBERS, so nothing here relies on that:
    the overage sits on the bill until an invoice takes it, and every new bill
    on the engagement says it is there.
    """
    import invoicing

    out = []
    for bill in invoicing.issued_for(Path(store), ref):
        pay = bill.get("_payment") or {}
        over = pay.get("over_by") or 0
        if over and not pay.get("over_applied"):
            out.append({"invoice": bill.get("InvoiceNumber", ""),
                        "cents": over})
    return out


def apply_overpayment(store: Path, ref: str, *, invoice: str,
                      applied_to: str) -> bool:
    """Write down that a bill's overage has been credited onto another bill.

    NAMED, NOT GUESSED. A credit that happens to equal the overage is not
    evidence that it IS the overage, so this is only called when the operator
    has put the overpaid invoice's number in the credit's own label -- which is
    also what makes the two bills readable side by side a year later.
    """
    for folder in sorted(Path(store).glob("*/invoices")):
        if folder.parent.name != ref:
            continue
        for path in sorted(folder.glob("*.json")):
            bill = json.loads(path.read_text(encoding="utf-8"))
            if bill.get("InvoiceNumber") != invoice:
                continue
            pay = dict(bill.get("_payment") or {})
            if not pay.get("over_by") or pay.get("over_applied"):
                return False
            pay["over_applied"] = applied_to
            bill["_payment"] = pay
            path.write_text(
                json.dumps(bill, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            return True
    return False


def settled_for(store: Path, ref: str) -> list[dict]:
    """Every settled invoice on one engagement. What `may_file` reads."""
    import invoicing

    return [b for b in invoicing.issued_for(Path(store), ref)
            if b.get("SettledOn")]
