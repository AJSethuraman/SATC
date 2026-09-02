"""A bill a client can pay, proved without a network.

THE FRONT-TO-BACK PROOF FOR THIS ONE IS SPLIT, and saying so is the point.
Square is unreachable from the environment this was built in — every
`squareup.com` host is blocked by the network policy — so not one real API call
was made here. These tests exercise every rule in `payments.py` against a
recorded transport: the idempotency key, the cents, the refusals, what gets
written and what deliberately does not. What they cannot prove is that Square
answers the way its documentation says. **That call happens on the firm's
machine, once, against the sandbox** (`python cli.py invoice --sandbox`), and
until it does this feature is built and not demonstrated. S28.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import invoicing  # noqa: E402
import payments  # noqa: E402


# ── a Square that answers, and remembers what it was asked ────────────────

class Recorder:
    """A stand-in for the network. Every call is kept so a test can read it."""

    def __init__(self, *, url="https://square.link/u/aB3xY9", state="OPEN",
                 fail=None):
        self.calls: list[tuple] = []
        self.url, self.state, self.fail = url, state, fail
        self.canned: dict | None = None

    def reply(self, payload: dict) -> None:
        """Answer the next order lookup with this exact body, so a test can
        put a shape on the wire that the default fake never produces."""
        self.canned = payload

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        if self.fail:
            raise payments.PaymentError(self.fail)
        if url.endswith("/payment-links"):
            return {"payment_link": {"id": "PL1", "order_id": "ORD1",
                                     "url": self.url}}
        if url.endswith("/batch-retrieve"):
            if self.canned is not None:
                return self.canned
            return {"orders": [{"id": oid, "state": self.state,
                                "total_money": {"amount": 64500},
                                "closed_at": "2027-03-04T10:00:00Z"}
                               for oid in body["order_ids"]]}
        return {}


@pytest.fixture
def square():
    rec = Recorder()
    return rec, payments.Square(token="sq0-secret", location_id="LOC1",
                                host="connect.squareupsandbox.com",
                                version="2026-01-22", transport=rec)


@pytest.fixture
def approved():
    """The registry as it reads once the firm has filled it in."""
    reg = json.loads(json.dumps(payments.settings()))
    reg["square"]["location_id"] = "LOC1"
    reg["square"]["sandbox_location_id"] = "LOC1-SANDBOX"
    reg["link_name"] = "<<FirmName>> — invoice <<InvoiceNumber>>"
    reg["payment_instruction"] = "Pay online by card at the link on this invoice."
    return reg


BILL = {"InvoiceNumber": "2027-0001", "AmountDue": "$645.00",
        "FirmName": "SAT-C LLP"}


# ── the trap this module was written around ───────────────────────────────

def test_it_does_not_reach_for_the_shadowed_requests_library():
    """`client-documents/requests.py` is this project's own module — the
    document request list — and it SHADOWS the HTTP library inside this
    package. `import requests` here returns the wrong thing entirely."""
    import requests

    assert Path(requests.__file__).parent == ROOT, (
        "the local module no longer shadows; the comment in payments.py is stale"
    )
    # THE STATEMENT, NOT THE PROSE. `payments.py` explains this trap in its
    # own docstring, so a substring search finds the warning and calls it the
    # bug. Only a line that actually imports counts.
    import re

    source = (ROOT / "payments.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import requests|from requests\b)", source,
                         re.M)
    assert "urllib.request" in source


# ── money crosses the boundary once, as an integer ────────────────────────

@pytest.mark.parametrize("amount,cents", [
    ("$645.00", 64500), ("$1,234.56", 123456), ("$275.08", 27508),
    (450, 45000), ("$0.99", 99),
])
def test_the_amount_becomes_integer_cents(amount, cents):
    """Square takes an integer of the smallest unit and `money.parse` returns a
    float. Rounding in one place is why $275.08 cannot become 27507.

    THE TYPE IS ASSERTED, NOT JUST THE VALUE. `64500.0 == 64500` is true in
    Python, so an equality check alone passes while a float goes on the wire —
    found by mutating `int(round(v * 100))` to `v * 100` and watching every
    test stay green."""
    got = payments._cents(amount)
    assert got == cents
    assert isinstance(got, int) and not isinstance(got, bool), (
        f"{got!r} is a {type(got).__name__}; Square takes an integer of the "
        f"smallest unit and a float serialises as 64500.0"
    )


@pytest.mark.parametrize("bad", ["[CONFIRM: what does this cost?]", "", None,
                                 "nothing", "$0.00", "-$5.00"])
def test_an_amount_a_link_cannot_be_made_for_is_refused(bad):
    with pytest.raises(payments.PaymentError):
        payments._cents(bad)


# ── the link ──────────────────────────────────────────────────────────────

def test_the_idempotency_key_is_the_invoice_number(square, approved):
    """Running `invoice` twice must not leave two live links against one bill,
    each able to take the money."""
    rec, api = square
    payments.link_for(BILL, using=api, reg=approved)
    payments.link_for(BILL, using=api, reg=approved)
    keys = [body["idempotency_key"] for _, _, _, body in rec.calls]
    assert keys == ["satc-2027-0001", "satc-2027-0001"]


def test_the_link_carries_the_invoice_number_where_it_can_be_read_back(square,
                                                                       approved):
    rec, api = square
    payments.link_for(BILL, using=api, reg=approved)
    _, _, _, body = rec.calls[0]
    assert body["payment_note"] == "2027-0001"
    assert body["quick_pay"]["price_money"] == {"amount": 64500,
                                                "currency": "USD"}
    assert body["quick_pay"]["location_id"] == "LOC1"


def test_the_name_the_client_sees_is_the_firms_and_is_filled_in(square,
                                                                approved):
    rec, api = square
    payments.link_for(BILL, using=api, reg=approved)
    assert rec.calls[0][3]["quick_pay"]["name"] == "SAT-C LLP — invoice 2027-0001"


def test_it_will_not_make_a_link_while_anything_is_unwritten(square):
    """The shipped registry still waits on the firm, so no link is made.

    Renamed and widened 30 Aug 2026. It used to assert the refusal came from the
    payment-page WORDING, and that reason was load-bearing by accident: while
    the copy carried a `[CONFIRM:` nothing reached the placeholder location_id
    behind it. The firm approved the wording and this test stopped firing --
    which is how the gap was found. link_for now refuses on every unwritten
    field, so approving one cannot open the door for another.
    """
    rec, api = square
    with pytest.raises(payments.PaymentError, match="waiting on the firm"):
        payments.link_for(BILL, using=api, reg=payments.settings())
    assert not rec.calls, "it called Square before checking"


def test_the_refusal_names_what_is_actually_missing(square):
    """A refusal that does not say which field is a puzzle, not a message."""
    _, api = square
    with pytest.raises(payments.PaymentError, match="square.location_id"):
        payments.link_for(BILL, using=api, reg=payments.settings())


def test_unapproved_wording_alone_still_refuses(square):
    """The original guarantee, kept: copy nobody approved never reaches Square."""
    rec, api = square
    reg = dict(payments.settings())
    reg["square"] = dict(reg["square"], location_id="L8XYZ0PQ4R2AB")
    reg["link_name"] = "[CONFIRM: something nobody has agreed]"
    with pytest.raises(payments.PaymentError, match="link_name"):
        payments.link_for(BILL, using=api, reg=reg)
    assert not rec.calls


def test_an_invoice_with_no_number_is_refused(square, approved):
    rec, api = square
    with pytest.raises(payments.PaymentError, match="idempotency"):
        payments.link_for({**BILL, "InvoiceNumber": ""}, using=api,
                          reg=approved)
    assert not rec.calls


def test_a_processor_that_answers_without_a_link_is_not_a_success(approved):
    class Empty(Recorder):
        def __call__(self, *a):
            super().__call__(*a)
            return {"payment_link": {}}

    api = payments.Square(token="t", location_id="L", host="h", version="v",
                          transport=Empty())
    with pytest.raises(payments.PaymentError, match="returned no link"):
        payments.link_for(BILL, using=api, reg=approved)


# ── the credential ────────────────────────────────────────────────────────

def test_the_token_is_read_from_the_environment_and_never_stored(monkeypatch,
                                                                 approved):
    monkeypatch.delenv("SATC_SQUARE_TOKEN", raising=False)
    with pytest.raises(payments.PaymentError, match="SATC_SQUARE_TOKEN"):
        payments.processor(reg=approved)
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "sq0-secret")
    assert payments.processor(reg=approved).token == "sq0-secret"

    registry = (ROOT / "registry" / "payments.yaml").read_text(encoding="utf-8")
    # THE NET STAYS BROAD. Square's credentials are `EAAA…` (access token),
    # `sq0atp-` (personal access token) and `sq0csp-` (application secret), but
    # banning only those three would let a future prefix through, so anything
    # beginning `sq0` is refused. The two APPLICATION id prefixes are the one
    # exception, written out here rather than loosened away: an application id
    # is public — it ships inside web payment pages — and the registry names
    # both shapes on purpose, because the firm sent one in place of a location
    # id and the comment that stops the next person doing the same has to be
    # able to say what it looks like.
    public = registry.replace("sq0idp-", "").replace("sq0idb-", "")
    assert "sq0" not in public and "token:" not in registry


def test_the_token_never_reaches_what_is_written_down(square, approved):
    """A link record goes into an engagement file that lives in OneDrive and is
    read back every season."""
    _, api = square
    link = payments.link_for(BILL, using=api, reg=approved)
    written = json.dumps(link.as_record())
    assert "sq0" not in written and "Authorization" not in written


def test_sandbox_and_production_are_different_hosts(monkeypatch, approved):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    assert "sandbox" in payments.processor(sandbox=True, reg=approved).host
    assert "sandbox" not in payments.processor(reg=approved).host


# ── settlement ────────────────────────────────────────────────────────────

def test_only_a_completed_order_counts_as_paid(square):
    rec, api = square
    rec.state = "OPEN"
    assert not api.settled(["ORD1"])["ORD1"].paid
    rec.state = "COMPLETED"
    got = api.settled(["ORD1"])["ORD1"]
    assert got.paid and got.when == "2027-03-04" and got.amount_cents == 64500


def test_it_asks_in_batches_the_processor_will_accept(square):
    rec, api = square
    api.settled([f"ORD{i}" for i in range(230)])
    sizes = [len(body["order_ids"]) for _, _, _, body in rec.calls]
    assert sizes == [100, 100, 30]


def _bill(tmp_path, due="$645.00", number="2027-0001"):
    """A bill on disk with the field the money is checked against.

    THE FIXTURES HERE USED TO CARRY NO `AmountDue`, which is why nothing in
    this file could notice that no code compared the money to the bill: the
    tests agreed with the code about a document neither of them had looked at.
    """
    path = tmp_path / f"{number}.json"
    path.write_text(json.dumps({"InvoiceNumber": number, "AmountDue": due}),
                    encoding="utf-8")
    return path


def test_an_unpaid_order_is_never_written_down(tmp_path):
    """A cached "no" goes stale the moment somebody pays, and a bill marked
    unpaid that has been settled is the error that reaches a client."""
    bill = _bill(tmp_path)
    assert not payments.record_settlement(
        bill, payments.Settlement("ORD1", "OPEN")).settled
    assert "SettledOn" not in json.loads(bill.read_text(encoding="utf-8"))


def test_a_settlement_is_written_once_and_not_rewritten(tmp_path):
    bill = _bill(tmp_path)
    paid = payments.Settlement("ORD1", "COMPLETED", 64500, "2027-03-04")
    posted = payments.record_settlement(bill, paid)
    assert posted.settled and not posted.problem
    assert json.loads(bill.read_text(encoding="utf-8"))["SettledOn"] == "2027-03-04"
    assert not payments.record_settlement(bill, paid).settled, "it wrote twice"


# ── the money is checked against the bill ─────────────────────────────────
#
# `deactivate` was written because "a link outliving its figure is the one way
# this feature takes the wrong amount", and then nothing ever compared the two
# amounts: `settled_amount` was written onto every bill and `grep` found no
# reader. These are the cases that were unguarded.


def test_a_short_payment_does_not_settle_the_bill(tmp_path):
    """The stale-link case, end to end: a link made at $645 collects $645
    after the engagement is re-quoted to $745. The bill is not covered, so it
    must not be marked settled -- `signing.may_file` reads settled bills, and
    every engagement letter promises no e-file before the invoice is."""
    bill = _bill(tmp_path, due="$745.00")
    posted = payments.record_settlement(
        bill, payments.Settlement("ORD1", "COMPLETED", 64500, "2027-03-04"))
    assert not posted.settled and posted.short
    assert posted.due_cents == 74500 and posted.arrived_cents == 64500
    assert "$100.00" in posted.problem, posted.problem

    written = json.loads(bill.read_text(encoding="utf-8"))
    assert "SettledOn" not in written, "a short payment settled the bill"
    assert written["_payment"]["short_by"] == 10000


def test_an_overpayment_settles_and_says_what_is_owed_back(tmp_path):
    """Holding a return hostage over the firm's own refund would be absurd.
    The bill is covered; somebody still owes the client the difference."""
    bill = _bill(tmp_path, due="$645.00")
    posted = payments.record_settlement(
        bill, payments.Settlement("ORD1", "COMPLETED", 74500, "2027-03-04"))
    assert posted.settled and not posted.short
    assert "$100.00" in posted.problem and "back" in posted.problem

    written = json.loads(bill.read_text(encoding="utf-8"))
    assert written["SettledOn"] == "2027-03-04"
    assert written["_payment"]["over_by"] == 10000


def test_what_arrived_beats_what_the_order_was_for(tmp_path):
    """A partial tender leaves the order total at the full figure. Reading the
    total would call a half-paid bill settled."""
    bill = _bill(tmp_path, due="$645.00")
    half = payments.Settlement("ORD1", "COMPLETED", 64500, "2027-03-04",
                               tendered_cents=32250)
    assert half.arrived_cents == 32250
    posted = payments.record_settlement(bill, half)
    assert not posted.settled and posted.short
    assert "SettledOn" not in json.loads(bill.read_text(encoding="utf-8"))


def test_tenders_are_read_off_the_order(square):
    rec, api = square
    rec.reply({"orders": [{"id": "ORD1", "state": "COMPLETED",
                           "total_money": {"amount": 64500},
                           "closed_at": "2027-03-04T18:00:00Z",
                           "tenders": [{"amount_money": {"amount": 30000}},
                                       {"amount_money": {"amount": 20000}}]}]})
    got = api.settled(["ORD1"])["ORD1"]
    assert got.tendered_cents == 50000 and got.arrived_cents == 50000


def test_a_bill_whose_figure_cannot_be_read_is_never_settled(tmp_path):
    """An invoice still carrying a `[CONFIRM:` has no figure to check money
    against. Settling it would be settling against nothing."""
    bill = _bill(tmp_path, due="[CONFIRM: the fee for this engagement]")
    posted = payments.record_settlement(
        bill, payments.Settlement("ORD1", "COMPLETED", 64500, "2027-03-04"))
    assert not posted.settled and posted.problem
    assert "SettledOn" not in json.loads(bill.read_text(encoding="utf-8"))


# ── a quote never gets a link ─────────────────────────────────────────────

# NO TEST HERE, AND THAT IS THE POINT.
#
# `test_only_the_invoice_may_carry_a_payment_link` used to sit in this spot,
# written and described as though it stopped something. It stopped nothing. A
# payment link cannot reach an estimate three ways over: invoice fields load
# only when the invoice is the document being rendered (`cli.cmd_render`), the
# estimate template carries no such token, and adding one would fail the render
# outright because `merge` refuses an unresolved field.
#
# The firm, 30 August 2026, on exactly this: "An optimal control entirely
# mitigates risk... it isn't even sensical to add invoice links to estimates."
# A check for the impossible is worse than no check -- it costs maintenance and
# it teaches a reader that the suite is full of things that might happen.
#
# The reason now lives where somebody tempted to add a link would be standing:
# the "Deliberately not here" list in `FIELDS - Fee Estimate.md`. See
# `docs/SOFTWARE-TENETS.md` S30.


def test_the_invoice_renders_with_and_without_a_link():
    """An invoice raised before any of this existed still has to render."""
    import merge
    import settings as firm

    base = json.loads((ROOT / "samples" / "tax-opening-package.json")
                      .read_text(encoding="utf-8"))
    fields = {**firm.firm_fields("2026"), **base,
              "InvoiceNumber": "2027-0001", "InvoiceDate": "March 2, 2027",
              "PeriodLabel": "2026 tax year", "Subtotal": "$785.00",
              "AmountDue": "$785.00", "VarianceNote": "",
              "PaymentInstruction": "Pay online by card.",
              "BillingContactName": "A", "BillingContactEmail": "a@b.c"}
    template = cli.TEMPLATE_DIR / cli.DOCUMENTS["invoice"][0]

    without = merge.render_file(template, fields).html
    assert "square.link" not in without
    # THE FLAG AND THE VALUE TOGETHER, which is what `Link.as_record` writes.
    # A condition is a flag and a value is a field; the block turns on the
    # flag, so a URL alone would render nothing and look like a bug in the
    # template rather than in the caller.
    with_link = merge.render_file(template, {
        **fields, **payments.Link(id="PL1", order_id="ORD1",
                                  url="https://square.link/u/aB3xY9",
                                  amount_cents=78500, invoice="2027-0001",
                                  created="2027-03-02").as_record()}).html
    assert "https://square.link/u/aB3xY9" in with_link
    assert 'href="https://square.link/u/aB3xY9"' in with_link


# ── the sandbox is a different account, not a different host ──────────────
#
# WHAT THIS PAIR EXISTS TO STOP. The host switched on `--sandbox` and the
# location id did not, so one field served two Square accounts. Testing meant
# editing `location_id` to the sandbox value; billing meant editing it back.
# The failure is not the test run -- it is the run AFTER the one somebody
# forgot to change back, where a real client is sent a link against a test
# location and the money has nowhere to land.

def _reg_with(**square):
    reg = json.loads(json.dumps(payments.settings()))
    reg["square"].update(square)
    return reg


def test_sandbox_uses_the_sandbox_location(monkeypatch):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "sandbox-token")
    api = payments.processor(sandbox=True, reg=_reg_with(
        location_id="LPROD", sandbox_location_id="LSANDBOX"))
    assert api.location_id == "LSANDBOX"
    assert api.host == "connect.squareupsandbox.com"
    assert api.sandbox is True


def test_production_uses_the_production_location(monkeypatch):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "live-token")
    api = payments.processor(sandbox=False, reg=_reg_with(
        location_id="LPROD", sandbox_location_id="LSANDBOX"))
    assert api.location_id == "LPROD"
    assert api.host == "connect.squareup.com"
    assert api.sandbox is False


def test_a_sandbox_run_is_not_blocked_by_the_unfilled_production_id(monkeypatch):
    """The firm can test before they have a live location, and vice versa.

    Only the id for the run being made is waiting on anybody.
    """
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "sandbox-token")
    reg = _reg_with(sandbox_location_id="LSANDBOX")   # production still [CONFIRM:]
    api = payments.processor(sandbox=True, reg=reg)
    assert api.location_id == "LSANDBOX"

    rec = Recorder()
    api._send = rec
    reg["link_name"] = "SATC <<InvoiceNumber>>"
    reg["payment_instruction"] = "Pay by card at the following link."
    payments.link_for(BILL, using=api, reg=reg)
    assert rec.calls[0][3]["quick_pay"]["location_id"] == "LSANDBOX"


def test_a_production_run_is_still_blocked_by_the_unfilled_production_id(monkeypatch):
    """The other half. Filling in the SANDBOX id must not open the live door."""
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "live-token")
    reg = _reg_with(sandbox_location_id="LSANDBOX")   # production still [CONFIRM:]
    with pytest.raises(payments.PaymentError, match="square.location_id"):
        payments.processor(sandbox=False, reg=reg)


def test_a_production_link_never_carries_the_sandbox_location(monkeypatch):
    """The bug stated as an assertion, at the only place it would show."""
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "live-token")
    reg = _reg_with(location_id="LPROD", sandbox_location_id="LSANDBOX")
    reg["link_name"] = "SATC <<InvoiceNumber>>"
    reg["payment_instruction"] = "Pay by card at the following link."
    api = payments.processor(sandbox=False, reg=reg)
    rec = Recorder()
    api._send = rec
    payments.link_for(BILL, using=api, reg=reg)
    assert rec.calls[0][3]["quick_pay"]["location_id"] == "LPROD"
    assert "LSANDBOX" not in json.dumps(rec.calls)


# ── the live check ────────────────────────────────────────────────────────
#
# The check itself is software and can lie the same way anything else can. It
# is exercised here through the same stand-in transport -- which is exactly the
# limit these tests have, and the reason the check exists.


class Console:
    """A Square that answers the check's questions."""

    def __init__(self, *, locations=None, state="OPEN"):
        self.calls = []
        self.locations = ([{"id": "LOC1-SANDBOX", "name": "SAT-C LLP",
                            "status": "ACTIVE", "currency": "USD"}]
                          if locations is None else locations)
        self.state = state

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, body))
        if url.endswith("/v2/locations"):
            return {"locations": self.locations}
        if url.endswith("/payment-links"):
            return {"payment_link": {"id": "PL9", "order_id": "ORD9",
                                     "url": "https://square.link/u/check"}}
        if url.endswith("/batch-retrieve"):
            return {"orders": [{"id": "ORD9", "state": self.state,
                                "total_money": {"amount": 100},
                                "closed_at": "2027-03-04T10:00:00Z",
                                "tenders": ([{"amount_money": {"amount": 100}}]
                                            if self.state == "COMPLETED"
                                            else [])}]}
        return {}


def test_the_check_stops_at_the_first_failure_and_says_how_far_it_got(approved):
    """S2: a check that examined two things and printed a tick is worse than
    one that failed. Nothing after a failed step is passed -- it is unreached,
    and the caller has to be able to tell the difference."""
    reg = json.loads(json.dumps(approved))
    reg["square"]["sandbox_location_id"] = "[CONFIRM: the sandbox location id]"
    steps, link, got = payments.live_check(sandbox=True, reg=reg)
    assert len(steps) == 1 and not steps[0].ok
    assert link is None and got is None


def test_the_check_never_prints_the_token(monkeypatch, approved):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "sq0-super-secret")
    steps, _, _ = payments.live_check(sandbox=True, reg=approved,
                                      transport=Console())
    assert "sq0-super-secret" not in json.dumps([s.__dict__ for s in steps])


def test_a_location_id_that_is_not_yours_stops_the_check(monkeypatch, approved):
    """The typo that is otherwise invisible until a client is standing at a
    checkout page that will not load."""
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    console = Console(locations=[{"id": "SOMEBODY-ELSE", "name": "Not you"}])
    steps, link, _ = payments.live_check(sandbox=True, reg=approved,
                                         transport=console)
    named = {s.name: s for s in steps}
    assert not named["the location id is one of yours"].ok
    assert "Not you" in named["the location id is one of yours"].detail
    assert link is None, "it made a link against a location that is not yours"


def test_an_unpaid_check_link_is_five_of_six(monkeypatch, approved):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    steps, link, got = payments.live_check(sandbox=True, reg=approved,
                                           transport=Console())
    assert len(steps) == payments.CHECK_STEPS
    assert sum(s.ok for s in steps) == payments.CHECK_STEPS - 1
    assert link.url == "https://square.link/u/check"
    assert not steps[-1].ok and not got.paid


def test_a_paid_check_link_is_six_of_six(monkeypatch, approved):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    steps, _, got = payments.live_check(sandbox=True, reg=approved,
                                        transport=Console(state="COMPLETED"))
    assert len(steps) == payments.CHECK_STEPS and all(s.ok for s in steps)
    assert got.paid and got.arrived_cents == 100


def test_the_check_link_is_the_same_link_all_day(monkeypatch, approved):
    """Re-running is the whole flow: open it, pay it, run it again. A second
    link each time would leave the paid one behind and report nothing."""
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    console = Console()
    for _ in range(2):
        payments.live_check(sandbox=True, reg=approved, transport=console)
    keys = [b["idempotency_key"] for _, url, b in console.calls
            if url.endswith("/payment-links")]
    assert len(keys) == 2 and keys[0] == keys[1]


def test_the_check_bills_itself_not_a_client(monkeypatch, approved):
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    console = Console()
    payments.live_check(sandbox=True, reg=approved, transport=console)
    note = next(b["payment_note"] for _, url, b in console.calls
                if url.endswith("/payment-links"))
    assert note.startswith(payments.CHECK_PREFIX)


# ── an overpayment is credited, not refunded ──────────────────────────────
#
# The firm, 2 September 2026, on being told an overpayment settles the bill:
# *"i am not eating a fee for them doing it... right?"* Right -- and the way
# not to is to put it on the next bill. Square stopped returning the processing
# fee on refunds to US sellers on 11 April 2023, so a refund costs the fee on
# money the firm never asked for and recovers none of it.


def _engagement(tmp_path, ref="SMITH-2026", bills=()):
    folder = tmp_path / ref / "invoices"
    folder.mkdir(parents=True)
    for bill in bills:
        (folder / f"{bill['InvoiceNumber']}.json").write_text(
            json.dumps(bill), encoding="utf-8")
    return tmp_path


def test_an_overpayment_says_credit_it_not_refund_it(tmp_path):
    bill = _bill(tmp_path, due="$645.00")
    posted = payments.record_settlement(
        bill, payments.Settlement("ORD1", "COMPLETED", 74500, "2027-03-04"))
    # Not "does it avoid the word refund" -- it has to say the word to say
    # why not to. What matters is that it names the cheaper move and the
    # reason, and that the bill still settled.
    assert posted.settled
    assert "credit" in posted.problem and "processing fee" in posted.problem
    assert "$100.00" in posted.problem


def test_an_overpayment_is_outstanding_until_a_bill_takes_it(tmp_path):
    store = _engagement(tmp_path, bills=[
        {"InvoiceNumber": "2027-0001", "AmountDue": "$645.00",
         "SettledOn": "2027-03-04",
         "_payment": {"order_id": "ORD1", "over_by": 10000}}])
    out = payments.unapplied_overpayments(store, "SMITH-2026")
    assert out == [{"invoice": "2027-0001", "cents": 10000}]

    assert payments.apply_overpayment(store, "SMITH-2026",
                                      invoice="2027-0001",
                                      applied_to="2027-0009")
    assert payments.unapplied_overpayments(store, "SMITH-2026") == []


def test_an_overpayment_is_never_given_back_twice(tmp_path):
    store = _engagement(tmp_path, bills=[
        {"InvoiceNumber": "2027-0001", "AmountDue": "$645.00",
         "SettledOn": "2027-03-04",
         "_payment": {"order_id": "ORD1", "over_by": 10000,
                      "over_applied": "2027-0009"}}])
    assert payments.unapplied_overpayments(store, "SMITH-2026") == []
    assert not payments.apply_overpayment(store, "SMITH-2026",
                                          invoice="2027-0001",
                                          applied_to="2027-0010")


def test_a_bill_that_was_paid_exactly_owes_nothing_back(tmp_path):
    store = _engagement(tmp_path, bills=[
        {"InvoiceNumber": "2027-0001", "AmountDue": "$645.00",
         "SettledOn": "2027-03-04",
         "_payment": {"order_id": "ORD1", "settled_amount": 64500}}])
    assert payments.unapplied_overpayments(store, "SMITH-2026") == []


def test_the_check_can_look_up_a_location_id_it_has_not_been_given(monkeypatch,
                                                                   approved):
    """The chicken and the egg: refusing to run until the id is written sent
    somebody into a web console to hunt for it, and what came back was the
    APPLICATION id, which is a different identifier entirely. The token can
    list the locations, so ask."""
    monkeypatch.setenv("SATC_SQUARE_TOKEN", "t")
    reg = json.loads(json.dumps(approved))
    reg["square"]["sandbox_location_id"] = "[CONFIRM: the sandbox location id]"
    steps, link, _ = payments.live_check(
        sandbox=True, reg=reg,
        transport=Console(locations=[{"id": "LREAL123", "name": "SAT-C LLP"}]))
    assert not steps[-1].ok
    assert "LREAL123" in steps[-1].detail and "SAT-C LLP" in steps[-1].detail
    assert link is None


def test_it_does_not_pretend_to_look_up_an_id_with_no_token(approved,
                                                            monkeypatch):
    """With no token there is nothing to ask WITH, so it must not try -- and
    must say the token is missing rather than reporting a failed lookup, which
    sends somebody debugging their Square account instead of their shell."""
    monkeypatch.delenv("SATC_SQUARE_TOKEN", raising=False)
    reg = json.loads(json.dumps(approved))
    reg["square"]["sandbox_location_id"] = "[CONFIRM: the sandbox location id]"

    def never(*args, **kwargs):
        raise AssertionError("it called Square with no token")

    steps, _, _ = payments.live_check(sandbox=True, reg=reg, transport=never)
    assert len(steps) == 1 and not steps[0].ok
    assert "is empty" in steps[0].detail
    assert "failed" not in steps[0].detail


# ── what a refusal says ───────────────────────────────────────────────────
#
# A 401 came back from a real sandbox run on 2 September 2026 and the message
# was `refused: 401 — This request could not be authorized..` -- a doubled full
# stop, and not one word about the likely cause. A bare status code sends
# somebody to look at their Square account when the fault is one field away.


def test_a_refusal_does_not_double_squares_full_stop():
    said = payments._refusal(
        401, "This request could not be authorized.",
        "https://connect.squareupsandbox.com/v2/locations")
    assert ".." not in said


def test_a_401_names_the_likeliest_cause_and_the_tab_to_look_at():
    """There are two accounts, each with its own token, and a token from one
    is always refused by the other. The console shows both, one click apart,
    beside two values that are not tokens at all."""
    sand = payments._refusal(401, "", "https://connect.squareupsandbox.com/x")
    assert "Sandbox" in sand and "Production token is always refused" in sand
    assert "application id" in sand and "application secret" in sand

    live = payments._refusal(401, "", "https://connect.squareup.com/x")
    assert "Production" in live and "Sandbox token is always refused" in live


def test_only_an_authorization_refusal_gets_the_token_advice():
    """A rate limit or a server fault has nothing to do with the token, and
    telling somebody to go and re-copy one would send them the wrong way."""
    for code in (400, 429, 500, 503):
        said = payments._refusal(code, "Something else.",
                                 "https://connect.squareup.com/x")
        assert "ACCESS TOKEN" not in said, code
        assert "Nothing has been put on the invoice." in said


def test_a_refusal_never_carries_the_request_or_the_token():
    """The request carries the Authorization header, and an exception string
    ends up in a terminal, a log, and whatever screenshot goes into a ticket."""
    said = payments._refusal(401, "nope", "https://connect.squareup.com/x")
    assert "Bearer" not in said and "Authorization" not in said
