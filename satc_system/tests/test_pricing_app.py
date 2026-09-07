"""The PRICES screen — changing what the practice charges, and the record of it.

Two decisions are being guarded here, and neither is about arithmetic.

**THE UI EDITS THE YAML.** Not a database override layered over the config. An
override wins silently over a hand edit, so the owner would change
``services.yaml``, see nothing happen, and have nothing on any screen tell them
why. So these tests assert on the FILE: what is in it after a good change, and —
just as hard — that it is byte-for-byte untouched after a refused one.

**THE EDIT IS SURGICAL.** In these two files the comments are the reasoning: the
whole argument for why a discount is shown rather than hidden lives in the header
of ``rate_plans.yaml``, and ``yaml.safe_dump`` would produce valid YAML with all
of it gone. So a change has to be a ONE-LINE diff, and
``test_a_change_is_a_one_line_diff_and_the_reasoning_survives`` is the test that
says so.

The recurring defect in this codebase gets its own section: a value the engine
rejects has to come back as a SENTENCE on the page, with what was typed still in
the box. Not a 500, and not an edit that silently went nowhere. Note what these
tests do NOT do — assert on wording invented in the view. The rules about what a
price may be live in ``satc.billing.editor`` and the catalogue loader, and this
screen's only job with a bad value is to put their refusal on the page unedited.

Everything drives the real ``create_app()`` over HTTP. A hand-registered
blueprint would pass whether or not ``server.py`` actually wires the screen up,
which is how a perfect screen ends up unreachable.
"""

from __future__ import annotations

import re
import shutil
from datetime import date, timedelta
from decimal import Decimal

import pytest

from satc.app.server import create_app
from satc.app.state import STATE
from satc.billing import catalogue, editor, next_invoice_number

# A client of our own. Issuing invoices in here must not change what any other
# screen's tests see for the seeded practice.
CLIENT = "SATC-PRICETEST"
YEAR = 2025

REAL_BILLING = catalogue.billing_dir()


@pytest.fixture()
def prices(tmp_path, monkeypatch):
    """A COPY of the practice's real billing config, which the test owns.

    Copied rather than synthesised on purpose. These tests are partly about what
    SURVIVES an edit — the header comments, the block scalars, the blank lines,
    the line endings — and a three-line fixture file has none of that to lose.
    The real file is never written to; ``billing_dir`` is redirected the way
    ``tests/test_price_config.py`` redirects it.

    The price record is emptied and the file fingerprints are dropped, so each
    test starts as a fresh install pointed at these two files. Without that, the
    previous test's edits would look to ``reconcile_files`` like somebody
    hand-editing the YAML between runs — which is a real thing it is supposed to
    notice, and pure noise here.
    """
    folder = tmp_path / "billing"
    folder.mkdir()
    for name in ("services.yaml", "rate_plans.yaml"):
        shutil.copyfile(REAL_BILLING / name, folder / name)
    monkeypatch.setattr(catalogue, "billing_dir", lambda *a, **k: folder)
    catalogue.forget_prices()

    STATE.store.mart.execute("DELETE FROM price_changes")
    STATE.store.mart.commit()
    for name in ("services.yaml", "rate_plans.yaml"):
        # The key ``satc.billing.history`` watches each priced file under. An
        # empty marker reads as "never looked", which is what a fresh install is.
        STATE.store.set_meta(f"price_watch:{name}", "")

    yield folder
    catalogue.forget_prices()


@pytest.fixture()
def web(prices):
    """The real app, exactly as it is served, reading the test's own prices."""
    return create_app().test_client()


def _text(resp) -> str:
    return resp.data.decode("utf-8")


def _rate(web, code, value, why="", stamp=""):
    return web.post("/pricing/rate", data={
        "code": code, "rate": value, "why": why, "stamp": stamp})


def _discount(web, key, value, why="", stamp=""):
    return web.post("/pricing/discount", data={
        "key": key, "discount_pct": value, "why": why, "stamp": stamp})


def _bytes(folder, name) -> bytes:
    return (folder / name).read_bytes()


# --- both screens render ------------------------------------------------------

def test_the_price_screen_renders_every_rate_and_every_discount(web, prices):
    """Grouped the way the picker groups them, so the owner reads the price list
    in the same shape they build an invoice in — and every one of them editable
    in place, not on a second screen."""
    resp = web.get("/pricing")
    assert resp.status_code == 200
    body = _text(resp)

    for category, svcs in catalogue.by_category():
        assert category in body
        for svc in svcs:
            assert svc.name in body
            assert svc.code in body
            assert f'value="{svc.standard_rate:.2f}"' in body
    for rp in catalogue.plans().values():
        assert rp.name in body
        assert f'value="{rp.discount_pct:g}"' in body


def test_the_history_screen_renders(web):
    resp = web.get("/pricing/history")
    assert resp.status_code == 200
    assert "Price history" in _text(resp)


def test_the_screen_says_the_file_is_still_the_truth(web, prices):
    """Principle 4 pointed at a UI: the owner has to be able to tell that this
    screen is a door onto the file rather than a competing store."""
    body = _text(web.get("/pricing"))
    assert str(prices / "services.yaml") in body
    assert str(prices / "rate_plans.yaml") in body
    assert "hand-editing" in body.lower()


# --- the refusal is the product ------------------------------------------------

def _refusal(body: str) -> str:
    """The sentence the screen is showing the owner, if it is showing one.

    Deliberately not matched against the engine's exact wording. What this screen
    owes the owner is that the refusal ARRIVES — as prose, naming the thing that
    was refused, on the page, with nothing written. The words themselves belong
    to ``satc.billing.editor`` and the catalogue loader and are theirs to
    improve; a copy of them asserted here would only mean nobody can improve them
    without a red test in a file that is not about them.
    """
    found = re.search(r'<p class="flag">(.*?)</p>', body, re.S)
    return " ".join(found.group(1).split()) if found else ""


@pytest.mark.parametrize("typed", [
    "four hundred", "", "12.4.5",
    # Decimal() accepts both of these and every guard written as a comparison
    # passes NaN silently. The invoice engine learned that one the hard way.
    "NaN", "Infinity",
    "-50",
])
def test_a_rate_the_engine_rejects_is_refused_on_the_page(web, prices, typed):
    """Never a 500, never a silently discarded edit, and never a byte written."""
    before = _bytes(prices, "services.yaml")
    resp = _rate(web, "return_1040", typed)

    assert resp.status_code == 200, "A bad rate must be a sentence, not a crash."
    said = _refusal(_text(resp))
    assert "return_1040" in said, (
        f"A refused rate has to come back as a sentence naming the service. "
        f"The page said: {said!r}")
    assert len(said) > 40, "A refusal that does not explain itself is a rejection."
    assert _bytes(prices, "services.yaml") == before, (
        "A refused rate must leave the file byte-for-byte as it was. Half-applying "
        "an edit the owner is about to be told was rejected is worse than either.")


@pytest.mark.parametrize("typed", ["-5", "140", "half", ""])
def test_a_discount_the_engine_rejects_is_refused_on_the_page(web, prices, typed):
    before = _bytes(prices, "rate_plans.yaml")
    resp = _discount(web, "household", typed)

    assert resp.status_code == 200
    said = _refusal(_text(resp))
    assert "household" in said, f"The page said: {said!r}"
    assert len(said) > 40
    assert _bytes(prices, "rate_plans.yaml") == before


def test_a_refused_rate_comes_back_with_the_typed_value_still_in_the_box(web, prices):
    """A refusal that also wipes the field makes the owner retype the value in
    order to read the complaint. The third time that happens they stop reading
    the complaint."""
    body = _text(_rate(web, "return_1040", "four hundred"))
    assert 'value="four hundred"' in body
    assert 'value="450.00"' not in body, (
        "The box that was refused must show what was typed, not quietly revert "
        "to the rate the owner was trying to change.")


def test_a_service_the_catalogue_does_not_have_is_a_sentence_not_a_500(web, prices):
    resp = _rate(web, "unicorn_grooming", "100")
    assert resp.status_code == 200
    assert "unicorn_grooming" in _text(resp)


def test_a_form_that_names_no_service_is_a_sentence(web, prices):
    resp = web.post("/pricing/rate", data={"rate": "500"})
    assert resp.status_code == 200
    assert "did not say which service" in _text(resp)


def test_a_billing_config_that_will_not_load_is_a_sentence_on_this_very_screen(web, prices):
    """The one screen the owner would go to in order to FIX a broken price list
    must not be the one screen a broken price list takes down."""
    (prices / "services.yaml").write_text(
        "services:\n  - code: x\n    unit: fixed\n    standard_rate: four\n",
        encoding="utf-8")
    catalogue.forget_prices()

    resp = web.get("/pricing")
    assert resp.status_code == 200
    assert "non-numeric rate" in _text(resp)


# --- a good change ------------------------------------------------------------

def test_a_good_change_writes_the_file_and_shows_up_immediately(web, prices):
    """Written to the YAML, live in the catalogue, and in the invoice picker on
    the very next page load — no restart, because a price edit that needs one is
    a price edit that silently did not happen."""
    resp = _rate(web, "return_1040", "495")
    assert resp.status_code == 200

    assert "standard_rate: 495" in (prices / "services.yaml").read_text("utf-8")
    assert catalogue.service("return_1040").standard_rate == Decimal("495")
    assert 'value="495.00"' in _text(web.get("/pricing"))
    assert "495.00" in _text(web.get("/invoices/new")), (
        "The picker the owner builds an invoice from has to be reading the same "
        "file this screen just wrote.")


def test_a_good_discount_change_writes_the_file_and_shows_up_immediately(web, prices):
    resp = _discount(web, "household", "30")
    assert resp.status_code == 200

    assert "discount_pct: 30" in (prices / "rate_plans.yaml").read_text("utf-8")
    assert catalogue.plan("household").discount_pct == Decimal("30")
    assert 'value="30"' in _text(web.get("/pricing"))


def test_a_change_is_a_one_line_diff_and_the_reasoning_survives(web, prices):
    """The decision this whole screen turns on.

    ``yaml.safe_dump`` would round-trip these files into valid YAML with every
    comment gone — and in these two files the comments ARE the reasoning. The
    header of ``rate_plans.yaml`` is the entire argument for why a discount is
    shown rather than hidden; deleting it is not a formatting change, it is the
    loss of the only record of why the practice prices the way it does.
    """
    before = (prices / "rate_plans.yaml").read_text("utf-8").splitlines()
    _discount(web, "hardship", "55")
    after = (prices / "rate_plans.yaml").read_text("utf-8").splitlines()

    assert len(before) == len(after), "A price change must not reflow the file."
    moved = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
    assert len(moved) == 1, (
        f"One value changed, so one line should differ. Lines that moved: "
        f"{[(before[i], after[i]) for i in moved]}")
    assert "discount_pct" in after[moved[0]]

    text = "\n".join(after)
    assert "THE DISCOUNT IS SHOWN, NOT HIDDEN" in text
    assert "Circular 230 §10.27" in text
    assert "A rough year — job loss, illness" in text, (
        "The block scalar explaining the hardship plan is part of the record too.")


def test_the_same_rate_again_changes_nothing_and_records_nothing(web, prices):
    """Principle 8, and principle 13. A history row saying 145 became 145 is a
    row that renders identically forever, and the record is worth reading a year
    later precisely because every row in it is a change."""
    before = _bytes(prices, "services.yaml")
    body = _text(_rate(web, "schedule_d", "145.00"))

    assert "already" in body
    assert _bytes(prices, "services.yaml") == before
    assert "No price has changed" in _text(web.get("/pricing/history"))


def test_an_edit_made_in_another_window_is_never_silently_overwritten(web, prices):
    """The promise the no-overrides decision was taken for, kept on the other
    side too. A tab left open over lunch while the YAML is hand-edited must not
    submit its stale value over the top of the hand edit."""
    stale = editor.file_stamp("services")
    (prices / "services.yaml").write_text(
        (prices / "services.yaml").read_text("utf-8")
        .replace("standard_rate: 450", "standard_rate: 4500"), encoding="utf-8")
    catalogue.forget_prices()

    body = _text(_rate(web, "return_1040", "475", stamp=stale))
    assert "changed on disk" in body
    assert "standard_rate: 4500" in (prices / "services.yaml").read_text("utf-8")


# --- the record ---------------------------------------------------------------

def test_the_history_shows_old_to_new_with_a_date_and_who(web, prices):
    _rate(web, "schedule_c", "310", why="Two hours of sorting, every time, since 2024")

    body = _text(web.get("/pricing/history?service=schedule_c"))
    assert "275" in body and "310" in body
    assert date.today().isoformat() in body
    assert "owner" in body
    assert "Two hours of sorting, every time, since 2024" in body


def test_a_change_may_say_why_but_is_never_required_to(web, prices):
    """Offered, not required. An unexplained change is still a fact, and refusing
    to record it because nobody typed a reason would lose the fact as well as the
    reason."""
    resp = _rate(web, "schedule_e_rental", "200")
    assert resp.status_code == 200
    assert catalogue.service("schedule_e_rental").standard_rate == Decimal("200")

    body = _text(web.get("/pricing/history?service=schedule_e_rental"))
    assert "200" in body
    assert "no reason recorded" in body


def test_the_history_filters_to_one_service(web, prices):
    _rate(web, "amended_return", "375")
    _rate(web, "bookkeeping_cleanup", "135")

    # The dropdown lists every subject on every view, so what is being checked
    # is the ROWS: the name of the thing that changed, as the table renders it.
    only = _text(web.get("/pricing/history?service=amended_return"))
    assert "<strong>Amended return</strong>" in only
    assert "<strong>Bookkeeping clean-up</strong>" not in only

    everything = _text(web.get("/pricing/history"))
    assert "<strong>Amended return</strong>" in everything
    assert "<strong>Bookkeeping clean-up</strong>" in everything


def test_a_rate_and_a_discount_do_not_read_alike_in_the_record(web, prices):
    """Principle 4's rule about two kinds of thing. 25 dollars off a return and
    25% off it are different changes, and a column that renders both as ``25`` is
    a column nobody can read a year later."""
    _discount(web, "fixed_income", "45")
    body = _text(web.get("/pricing/history?service=fixed_income"))
    assert "40%" in body and "45%" in body


def test_a_price_nobody_has_touched_says_so_rather_than_showing_a_date(web, prices):
    """Principle 1. "Never changed here" and "changed a long time ago" are
    different facts, and the second must not be invented from the absence of the
    first."""
    assert "never changed here" in _text(web.get("/pricing"))


def test_a_hand_edit_is_recorded_with_no_author_rather_than_left_out(web, prices):
    """Hand-editing the YAML stays supported, so the record has to be able to
    hold a change SATC did not make. A gap in a record looks exactly like nothing
    having happened, and an authorless row that says so is better — but it must
    never be attributed to the owner, who did not do it here."""
    web.get("/pricing")                      # SATC reads the files for the first time
    (prices / "services.yaml").write_text(
        (prices / "services.yaml").read_text("utf-8")
        .replace("standard_rate: 1250", "standard_rate: 1400", 1), encoding="utf-8")
    catalogue.forget_prices()

    screen = _text(web.get("/pricing"))
    assert "changed in the file since" in screen
    assert "author not recorded" in screen
    assert "human:owner" not in screen, (
        "The price list's own 'last changed' column has to distinguish a change "
        "SATC made from one it merely noticed. Putting the owner's handle on a "
        "change they did not make is a fabricated fact in the one column a later "
        "reader would rely on — and the distinction is worth nothing if it only "
        "exists on the screen nobody is looking at.")

    body = _text(web.get("/pricing/history?service=return_1065"))
    assert "author not recorded" in body
    assert "owner" not in body, (
        "SATC noticed this change; it did not make it. A row claiming otherwise "
        "is a fabricated fact in the one column a later reader would rely on.")


def test_the_record_answers_what_a_rate_was_on_a_day(web, prices):
    """The question the record exists to answer, asked from the screen — with
    the basis, because the number gets quoted to a client."""
    _rate(web, "planning_session", "225")

    today = date.today().isoformat()
    body = _text(web.get(f"/pricing/history?service=planning_session&on={today}"))
    assert "225.00" in body
    assert "How we know" in body


def test_a_date_before_the_record_began_is_refused_not_extrapolated(web, prices):
    """Principle 1 and principle 5. Running today's rate backwards past the day
    SATC started watching is a confident wrong answer about money — and it is the
    same number the owner could have read off the price list, dressed up as
    history."""
    web.get("/pricing")
    long_ago = (date.today() - timedelta(days=900)).isoformat()

    body = _text(web.get(f"/pricing/history?service=planning_session&on={long_ago}"))
    assert "Not recorded" in body
    assert "the price record begins on" in body


def test_a_date_that_is_not_a_date_is_a_sentence(web, prices):
    body = _text(web.get("/pricing/history?service=planning_session&on=last+March"))
    assert "is not a date" in body


def test_the_record_is_still_readable_when_the_config_will_not_parse(web, prices):
    """The history is a fact of its own. Losing the whole record because a rate
    was mistyped this morning would be the record failing on the day it is most
    needed — and this is the screen somebody is on while fixing it."""
    _rate(web, "notice_response", "225", why="Two of these took a full afternoon")

    (prices / "services.yaml").write_text("services: [", encoding="utf-8")
    catalogue.forget_prices()

    resp = web.get("/pricing/history")
    assert resp.status_code == 200
    body = _text(resp)
    assert "notice_response" in body
    assert "225" in body


# --- what a change does, and does not, reach -----------------------------------

def _issue_an_invoice(web, *, plan_key="standard", basis="", code="return_1040"):
    """Build and issue one invoice through the real billing screens."""
    web.post("/invoices/new", data={
        "action": "header", "client_id": CLIENT, "plan_key": plan_key,
        "plan_basis": basis, "tax_year": str(YEAR)})
    web.post("/invoices/new", data={
        "action": "add", "service_code": code, "quantity": "1"})
    number = next_invoice_number(STATE.store.load_invoices(), year=date.today().year)
    resp = web.post(f"/invoices/{number}/issue", data={"due_in_days": "30"})
    assert resp.status_code == 302, _text(resp)
    return resp.headers["Location"].rsplit("/", 1)[-1]


def _stored(invoice_id):
    return next(i for i in STATE.store.load_invoices() if i.invoice_id == invoice_id)


def test_an_issued_invoice_does_not_move_when_the_rate_behind_it_changes(web, prices):
    """The promise this screen makes on the page, checked against the engine.

    ``InvoiceLine.standard_rate`` is written onto the line by ``Invoice.add`` and
    ``standard_total`` sums it, so nothing on an issued invoice reads the
    catalogue again. If this ever goes red, the sentence on /pricing is a lie and
    has to change in the same commit.
    """
    invoice_id = _issue_an_invoice(web)
    was = _stored(invoice_id).total
    assert was == Decimal("450.00")

    _rate(web, "return_1040", "600")
    assert catalogue.service("return_1040").standard_rate == Decimal("600")

    after = _stored(invoice_id)
    assert after.total == was
    assert after.standard_total == was
    assert after.lines[0].standard_rate == Decimal("450")
    assert "450.00" in _text(web.get(f"/invoices/{invoice_id}"))


def test_the_screen_says_a_rate_change_does_not_reprice_what_is_issued(web, prices):
    assert "does not re-price anything already issued" in _text(web.get("/pricing"))


def test_changing_a_discount_does_NOT_move_an_issued_invoice(web, prices):
    """A DEFECT, pinned rather than papered over.

    ``Invoice.rate_plan`` is a property that calls ``plan(self.plan_key)`` every
    time it is read, so ``discount_total`` and ``total`` are recomputed from
    whatever ``rate_plans.yaml`` says NOW. Move a discount and every issued
    invoice on that plan reprices — including the copy the client is holding and
    the billed-to-date figures.

    FIXED: issue() now stamps the percentage onto the invoice, the way each
    line already stamped the rate. This test was written to go red when that
    happened, and it did — the sentence on /pricing was corrected in the same
    commit, which is what the note it carried asked for.
    """
    invoice_id = _issue_an_invoice(
        web, plan_key="household", basis="Ordinary household return")
    assert _stored(invoice_id).total == Decimal("337.50")     # 450 less 25%

    _discount(web, "household", "50")

    assert _stored(invoice_id).total == Decimal("337.50"), (
        "a discount change restated what a client had already paid")


def test_the_screen_says_what_a_discount_change_actually_does(web, prices):
    """The page said the opposite for one afternoon, and it was true when it
    said it. The engine was fixed rather than the sentence softened — so this
    guards that the two stay in step, in either direction."""
    page = _text(web.get("/pricing"))
    assert "does NOT move invoices already issued" in page
    assert "Drafts you have not issued yet DO follow the new number" in page
