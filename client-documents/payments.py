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

NOTHING HERE HOLDS A CREDENTIAL. The token is read from the environment at the
moment of a call and never stored, logged, echoed in an error, or written to any
engagement file. Tests assert that.
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

# States a Square order reaches. `COMPLETED` is the only one that means money
# arrived; `OPEN` is a link nobody has paid yet, and reading it as anything else
# would mark a bill settled because somebody looked at the page.
PAID = "COMPLETED"


class PaymentError(RuntimeError):
    """Something that would put a wrong link, or a wrong figure, on a bill."""


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
    """What the processor says about one order."""
    order_id: str
    state: str
    amount_cents: int = 0
    when: str = ""

    @property
    def paid(self) -> bool:
        return self.state == PAID


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
                 version: str, transport: Callable | None = None):
        self.token = token
        self.location_id = location_id
        self.host = host
        self.version = version
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
                )
        return out

    def deactivate(self, link: Link) -> None:
        """Take a link out of service. Used when a bill is re-quoted.

        A LINK OUTLIVING ITS FIGURE IS THE ONE WAY THIS FEATURE TAKES THE WRONG
        AMOUNT. Re-price an engagement from $645 to $745 and the old link will
        still cheerfully collect $645.
        """
        self._call("DELETE", f"/v2/online-checkout/payment-links/{link.id}")


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
        raise PaymentError(
            f"the payment processor refused: {exc.code}"
            + (f" — {detail}" if detail else "")
            + ". Nothing has been put on the invoice."
        ) from None
    except urllib.error.URLError as exc:
        raise PaymentError(
            f"the payment processor could not be reached ({exc.reason}). The "
            f"invoice is unchanged; try again when the network is back."
        ) from None
    return json.loads(raw) if raw else {}


def processor(*, sandbox: bool = False, transport: Callable | None = None,
              reg: dict | None = None) -> Square:
    """The configured processor, or a refusal saying what is missing."""
    reg = reg if reg is not None else settings()
    which = reg.get("processor", "")
    if which != "square":
        raise PaymentError(
            f"`registry/payments.yaml` selects the processor {which!r}, and "
            f"only `square` is implemented. The seam is there; the adapter is "
            f"not written."
        )
    conf = reg.get("square") or {}
    waiting = [p for p in unwritten(reg) if p.startswith("square.")]
    if waiting:
        raise PaymentError(
            "the payments registry is not filled in yet — "
            + ", ".join(waiting) + " is still a `[CONFIRM: ]`."
        )
    env = conf.get("token_env") or "SATC_SQUARE_TOKEN"
    token = os.environ.get(env, "").strip()
    if not token:
        raise PaymentError(
            f"no payment token in ${env}. It is read from the environment on "
            f"purpose and is never stored here — a token in the repository is "
            f"a token in every clone, backup and screenshot."
        )
    return Square(token=token, location_id=conf.get("location_id", ""),
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
    # without anyone remembering to come back here.
    waiting = unwritten(reg)
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


def record_settlement(path: Path, got: Settlement) -> bool:
    """Write a settlement onto its invoice. Returns whether anything moved.

    THE PROCESSOR IS THE SYSTEM OF RECORD FOR MONEY, and this is a cache of its
    answer -- which is why it is written onto the bill rather than into an
    append-only log. What must never be cached is a NEGATIVE: an unpaid order
    is simply left alone, so nothing here can mark a bill unpaid that the
    processor has since settled.
    """
    if not got.paid:
        return False
    bill = json.loads(Path(path).read_text(encoding="utf-8"))
    if bill.get("SettledOn"):
        return False
    bill["SettledOn"] = got.when or date.today().isoformat()
    bill["_payment"] = {**(bill.get("_payment") or {}), "state": got.state,
                        "settled_amount": got.amount_cents}
    Path(path).write_text(json.dumps(bill, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return True


def settled_for(store: Path, ref: str) -> list[dict]:
    """Every settled invoice on one engagement. What `may_file` reads."""
    import invoicing

    return [b for b in invoicing.issued_for(Path(store), ref)
            if b.get("SettledOn")]
