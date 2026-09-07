"""What the practice charged in March, and who moved it.

The price record exists to answer a question a config file structurally cannot:
a YAML file only ever says what the rate is *now*. A client queries a bill, a
quote given in February is honoured in May, last season is compared with this
one — and the answer has to be a recorded fact rather than today's number
dressed up as history.

Two failures are guarded here above all others:

* **A silent gap.** The owner still edits configs/billing/*.yaml by hand, and
  always will. A record that only knew about changes made through the app would
  look complete and be wrong, and a gap reads as "nothing happened".
* **A borrowed author.** A row that says a human changed a price when no human
  did is worse than a row that admits it does not know.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from satc.billing import catalogue, history
from satc.billing.invoice import BillingError
from satc.models.actor import Actor, ActorRefused
from satc.persistence import SATCStore

SERVICES = """
# The comments in this file are the reasoning, and a rate edit must not eat them.
services:
  - code: return_1040
    name: "Individual return"
    client_label: "Your federal individual tax return"
    category: "Tax returns"
    unit: fixed
    standard_rate: {rate}
"""

PLANS = """
meta:
  default_plan: standard
plans:
  - key: standard
    name: "Standard"
    discount_pct: 0
  - key: household
    name: "Household rate"
    discount_pct: {discount}
    requires_basis: true
"""

JAN = date(2026, 1, 5)
MAR = date(2026, 3, 10)
JUN = date(2026, 6, 1)
JUL = date(2026, 7, 1)


@pytest.fixture
def prices(tmp_path, monkeypatch):
    """A billing config the test owns, wired in where the app reads from."""
    folder = tmp_path / "billing"
    folder.mkdir()
    monkeypatch.setattr(catalogue, "billing_dir", lambda *a, **k: folder)
    catalogue.forget_prices()
    write_rate(folder, 450)
    write_discount(folder, 25)
    yield folder
    catalogue.forget_prices()


@pytest.fixture
def store(tmp_path):
    with SATCStore(tmp_path / "data") as open_store:
        yield open_store


def write_rate(folder, rate) -> None:
    (folder / "services.yaml").write_text(SERVICES.format(rate=rate), encoding="utf-8")


def write_discount(folder, discount) -> None:
    (folder / "rate_plans.yaml").write_text(PLANS.format(discount=discount),
                                            encoding="utf-8")


def owner_changes_rate(store, folder, *, old, new, on) -> history.PriceChange:
    """The app's own path: write the file, then record what was done."""
    write_rate(folder, new)
    return history.record_change(
        store, kind=history.SERVICE, subject="return_1040",
        field=history.STANDARD_RATE, old_value=old, new_value=new,
        actor=Actor.owner(), changed_on=on)


# --- the record itself ------------------------------------------------------


def test_a_change_round_trips_through_sqlite_with_both_values(prices, store):
    """Old AND new. A record that kept only the new value is the config file
    again, and answers nothing the file could not."""
    written = owner_changes_rate(store, prices, old=450, new=495, on=MAR)

    reloaded, = history.changes_for(store, "return_1040")
    assert reloaded == written              # every field, not just the ones below
    assert reloaded.old_value == "450"
    assert reloaded.new_value == "495"
    assert reloaded.old_rate == Decimal(450)
    assert reloaded.new_rate == Decimal(495)
    assert reloaded.changed_on == MAR
    assert reloaded.changed_by == Actor.owner()
    assert reloaded.author_is_recorded
    assert reloaded.change_id == written.change_id
    assert reloaded.recorded_at == written.recorded_at


def test_a_change_survives_a_fresh_process(prices, store, tmp_path):
    """The whole point is that it outlives the session that made it."""
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    store.close()

    with SATCStore(tmp_path / "data") as reopened:
        reloaded, = history.all_changes(reopened)
    assert (reloaded.old_value, reloaded.new_value) == ("450", "495")
    assert reloaded.changed_by == Actor.owner()


def test_the_same_change_recorded_twice_is_recorded_once(prices, store):
    """Principle 8. A double-submitted form is not two price rises."""
    first = owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    again = owner_changes_rate(store, prices, old=450, new=495, on=MAR)

    assert again.change_id == first.change_id
    assert len(history.all_changes(store)) == 1
    rows = store.mart.execute("SELECT COUNT(*) AS n FROM price_changes").fetchone()["n"]
    assert rows == 1


def test_two_changes_on_the_same_day_are_two_changes_in_order(prices, store):
    """A pricing pass moves a rate and corrects it ten minutes later. Both
    happened, both are kept, and the ORDER is recorded rather than left to the
    ids — asked which rate was in force that day, "whichever hashed higher" is
    a coin flip answering a question about money.

    450 → 500 → 550 is not an arbitrary example: those two changes hash into the
    OPPOSITE of the order they happened in, so a tie broken by change_id gets
    this wrong. With friendlier numbers the check passes either way and proves
    nothing (principle 12).
    """
    history.reconcile_files(store, today=JAN)
    write_rate(prices, 500)
    history.record_change(
        store, kind=history.SERVICE, subject="return_1040",
        field=history.STANDARD_RATE, old_value=450, new_value=500,
        actor=Actor.owner(), changed_on=MAR,
        recorded_at=datetime(2026, 3, 10, 9, 15))
    write_rate(prices, 550)
    history.record_change(
        store, kind=history.SERVICE, subject="return_1040",
        field=history.STANDARD_RATE, old_value=500, new_value=550,
        actor=Actor.owner(), changed_on=MAR, note="meant 550, not 500",
        recorded_at=datetime(2026, 3, 10, 9, 25))

    recorded = history.changes_for(store, "return_1040")
    assert [(c.old_value, c.new_value) for c in recorded] == [("450", "500"),
                                                              ("500", "550")]
    assert recorded[0].change_id > recorded[1].change_id, (
        "the values were chosen so that id order and true order disagree; if "
        "this ever stops being true the test below proves nothing")
    assert history.rate_on(store, "return_1040", MAR, today=JUL).rate == Decimal(550)


def test_a_reformatted_rate_is_not_a_price_change(prices, store):
    """450 and 450.00 are the same rate. A record that announced a change every
    time the owner tidied the file is the noise principle 13 warns about."""
    history.reconcile_files(store, today=JAN)
    write_rate(prices, "450.00")
    assert history.reconcile_files(store, today=MAR) == []


# --- who may write it -------------------------------------------------------


def test_a_model_may_not_change_what_the_practice_charges(prices, store):
    """Principle 6, at the engine rather than in a prompt. And note what is
    being refused: not just the price move, but the RECORD saying a human made
    it."""
    with pytest.raises(ActorRefused) as refusal:
        history.record_change(
            store, kind=history.SERVICE, subject="return_1040",
            field=history.STANDARD_RATE, old_value=450, new_value=1,
            actor=Actor.model("qwen3:8b"), changed_on=MAR)

    assert "qwen3:8b" in str(refusal.value)
    assert "owner" in str(refusal.value)            # names the right next step
    assert history.all_changes(store) == []         # and nothing was written


def test_a_sweep_may_not_either(prices, store):
    """A system actor is not a human. Deterministic code can be read and proved,
    which is why it may auto-confirm a reading — it is still not the person whose
    policy a price is."""
    with pytest.raises(ActorRefused):
        history.record_change(
            store, kind=history.SERVICE, subject="return_1040",
            field=history.STANDARD_RATE, old_value=450, new_value=495,
            actor=Actor.system("nightly"), changed_on=MAR)
    assert history.all_changes(store) == []


def test_the_record_refuses_to_disagree_with_the_file(prices, store):
    """The file is the source of truth. A record claiming 495 while the file
    says 450 is worse than no record, because nothing says which is right."""
    with pytest.raises(BillingError) as refusal:
        history.record_change(
            store, kind=history.SERVICE, subject="return_1040",
            field=history.STANDARD_RATE, old_value=450, new_value=495,
            actor=Actor.owner(), changed_on=MAR)      # file never written

    assert "services.yaml" in str(refusal.value)
    assert "first" in str(refusal.value)              # names the order to do it in
    assert history.all_changes(store) == []


# --- the edits SATC did not make -------------------------------------------


def test_the_first_look_records_nothing_and_starts_watching(prices, store):
    """Nothing to compare against yet. Inventing a change out of the first
    sighting would put a movement that never happened in the record."""
    assert history.reconcile_files(store, today=JAN) == []
    assert history.record_begins(store, history.SERVICE) == JAN


def test_an_edit_made_outside_the_app_is_recorded_as_authorless(prices, store):
    """The honest part. The owner edits the YAML in an editor at midnight — and
    a record that stayed silent would show a gap, which looks exactly like
    nothing having happened (principles 1 and 2)."""
    history.reconcile_files(store, today=JAN)
    write_rate(prices, 495)                      # not through the app

    noticed, = history.reconcile_files(store, today=MAR)

    assert noticed.subject == "return_1040"
    assert noticed.old_value == "450" and noticed.new_value == "495"
    assert noticed.changed_by is None, (
        "SATC noticed this change; it did not make it. Crediting the engine "
        "would put a fabricated author in the one column a reader relies on.")
    assert noticed.author_label == "author not recorded"
    assert noticed.not_before == JAN and noticed.changed_on == MAR
    assert noticed.when_label == f"between {JAN} and {MAR}"
    assert "outside the app" in noticed.note
    assert history.changes_for(store, "return_1040") == [noticed]


def test_an_outside_edit_is_noticed_once_not_on_every_page_load(prices, store):
    history.reconcile_files(store, today=JAN)
    write_rate(prices, 495)

    assert len(history.reconcile_files(store, today=MAR)) == 1
    assert history.reconcile_files(store, today=MAR) == []
    assert len(history.all_changes(store)) == 1


def test_a_change_the_owner_made_is_not_re_reported_as_a_stranger_s(prices, store):
    """Without the re-fingerprint, the app's own edit is rediscovered a moment
    later and recorded a second time with no author — the record calling the
    owner a stranger in their own log."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)

    assert history.reconcile_files(store, today=JUN) == []
    recorded, = history.all_changes(store)
    assert recorded.changed_by == Actor.owner()


def test_a_backdated_change_does_not_rewind_what_the_record_last_saw(prices, store):
    """Dating a change to last Monday does not mean SATC stopped watching then.

    If it did, the next hand edit would be reported as having happened somewhere
    in a window that includes days the record can fully account for — an honest
    admission of ignorance where there is none, which is its own kind of noise.
    """
    history.reconcile_files(store, today=JUN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)   # backdated
    write_rate(prices, 525)

    noticed, = history.reconcile_files(store, today=JUL)
    assert noticed.not_before == JUN


def test_a_comment_only_edit_moves_the_file_but_not_the_record(prices, store):
    """The record is of what the practice charges, not of when a file was saved.

    This also proves the detector is not simply shouting whenever the hash
    moves: the comments in these files are the reasoning, and editing them is a
    thing the owner should be able to do without the log inventing a price."""
    history.reconcile_files(store, today=JAN)
    path = prices / "services.yaml"
    path.write_text("# a new note about why\n" + path.read_text(encoding="utf-8"),
                    encoding="utf-8")

    assert history.reconcile_files(store, today=MAR) == []


def test_an_outside_edit_to_a_discount_is_recorded_too(prices, store):
    """Both priced files are watched. A discount is what the practice charges
    just as much as a rate is."""
    history.reconcile_files(store, today=JAN)
    write_discount(prices, 30)

    noticed, = history.reconcile_files(store, today=MAR)
    assert noticed.kind == history.RATE_PLAN
    assert noticed.subject == "household"
    assert (noticed.old_value, noticed.new_value) == ("25", "30")
    assert noticed.changed_by is None


def test_a_service_added_by_hand_says_it_was_not_there_before(prices, store):
    """``None`` for the old value means NOT RECORDED, so a row where the true
    answer is "it did not exist" has to say which of the two it is."""
    history.reconcile_files(store, today=JAN)
    (prices / "services.yaml").write_text(SERVICES.format(rate=450) + """
  - code: planning_session
    name: "Planning conversation"
    client_label: "Tax planning conversation"
    category: "Advice"
    unit: per_hour
    standard_rate: 200
""", encoding="utf-8")

    noticed, = history.reconcile_files(store, today=MAR)
    assert noticed.subject == "planning_session"
    assert noticed.old_value is None and noticed.new_value == "200"
    assert "not in the file before" in noticed.note
    assert noticed.value_label(noticed.old_value) == "not recorded"


# --- what were we charging in March? ---------------------------------------


def test_rate_on_answers_before_between_and_after_two_changes(prices, store):
    """The question the record exists for."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    owner_changes_rate(store, prices, old=495, new=525, on=JUN)

    before = history.rate_on(store, "return_1040", date(2026, 2, 1), today=JUL)
    between = history.rate_on(store, "return_1040", date(2026, 4, 1), today=JUL)
    after = history.rate_on(store, "return_1040", date(2026, 6, 15), today=JUL)

    assert before.rate == Decimal(450)
    assert between.rate == Decimal(495)
    assert after.rate == Decimal(525)
    # The number never travels without how we know it.
    assert str(MAR) in before.basis and str(JUN) in after.basis
    assert "owner" in between.basis


def test_rate_on_the_day_of_a_change_is_the_new_rate(prices, store):
    """A change takes effect the day it is made — the record is not vague about
    its own edges."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)

    assert history.rate_on(store, "return_1040", MAR, today=JUL).rate == Decimal(495)
    assert history.rate_on(store, "return_1040", date(2026, 3, 9),
                           today=JUL).rate == Decimal(450)


def test_rate_on_refuses_a_date_before_the_record_began(prices, store):
    """Principle 1. Extrapolating today's rate backwards past the day SATC
    started watching is inventing a value — and it is the kind that gets quoted
    to a client with a straight face."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)

    answer = history.rate_on(store, "return_1040", date(2025, 12, 1), today=JUL)
    assert answer.rate is None
    assert not answer.is_known
    assert str(JAN) in answer.basis            # says when the record does start
    assert "git log" in answer.basis           # names where the answer might be
    assert "not recorded" in str(answer)


def test_rate_on_refuses_a_date_inside_an_outside_edit_s_window(prices, store):
    """All SATC knows is that the file said one thing in January and another in
    March. A bill dated February deserves "the record cannot say" rather than a
    confident answer on a coin flip (principle 5)."""
    history.reconcile_files(store, today=JAN)
    write_rate(prices, 495)
    history.reconcile_files(store, today=MAR)

    answer = history.rate_on(store, "return_1040", date(2026, 2, 1), today=JUL)
    assert answer.rate is None
    assert "450" in answer.basis and "495" in answer.basis   # it was one of these
    assert str(JAN) in answer.basis and str(MAR) in answer.basis


def test_an_unchanged_rate_is_answerable_back_to_the_day_watching_began(prices, store):
    """No changes recorded and the file never moved means the rate did not move
    — that is a recorded fact, not a guess, and refusing it would make the
    record useless in its most ordinary case."""
    history.reconcile_files(store, today=JAN)

    answer = history.rate_on(store, "return_1040", date(2026, 2, 1), today=JUL)
    assert answer.rate == Decimal(450)
    assert str(JAN) in answer.basis


def test_rate_on_today_reads_the_file_and_flags_a_record_that_lags_it(prices, store):
    """The file is the source of truth. A record silently outranking a hand edit
    is the trap this design was chosen to avoid: you change the file, nothing
    happens, and nothing says why."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    write_rate(prices, 600)                 # by hand, and not yet reconciled

    answer = history.rate_on(store, "return_1040", JUL, today=JUL)
    assert answer.rate == Decimal(600)
    assert "495" in answer.basis            # and says the record has not caught up


def test_rate_on_refuses_a_code_the_catalogue_has_never_heard_of(prices, store):
    history.reconcile_files(store, today=JAN)
    answer = history.rate_on(store, "return_1120s", date(2026, 2, 1), today=JUL)
    assert answer.rate is None
    assert "return_1120s" in answer.basis


def test_rate_on_still_answers_history_when_todays_file_is_broken(prices, store):
    """A typo saved five minutes ago must not take the past with it. The refusal
    still happens loudly where the catalogue itself is loaded."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    (prices / "services.yaml").write_text(SERVICES.format(rate="four hundred"),
                                          encoding="utf-8")

    assert history.rate_on(store, "return_1040", date(2026, 4, 1),
                           today=JUL).rate == Decimal(495)


def test_a_rate_that_moves_does_not_reprice_an_invoice_already_raised(prices, store):
    """The claim this whole module rests on, checked rather than assumed.

    ``InvoiceLine.standard_rate`` is copied onto the line when the line is
    added, so an issued invoice already carries the price it was raised at and
    needs nothing from the price record. If it did NOT, a rate rise in March
    would silently restate every bill sent in February — and this record would
    have to become the thing invoices are priced from, which is a different and
    much larger design.
    """
    from satc.billing.invoice import Invoice

    invoice = Invoice(invoice_id="2026-0001", client_id="C-100", tax_year=2025)
    invoice.add("return_1040")
    invoice.issue(on=date(2026, 2, 20))
    assert invoice.total == Decimal("450.00")

    owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    catalogue.forget_prices()

    assert invoice.lines[0].standard_rate == Decimal(450)
    assert invoice.total == Decimal("450.00")
    assert catalogue.service("return_1040").standard_rate == Decimal(495)


# --- the record on disk ----------------------------------------------------

_LEGACY_PRICE_DDL = """
CREATE TABLE price_changes (
  change_id TEXT PRIMARY KEY, kind TEXT, subject TEXT, field TEXT,
  old_value TEXT, new_value TEXT, changed_on TEXT, changed_by TEXT);
"""
"""A first cut of the table, without the two columns that carry the honesty.

``CREATE TABLE IF NOT EXISTS`` never alters a table that already exists, so this
is what would genuinely be on the owner's disk — and a migration that only works
on a database created after the migration was written is not a migration. This
repo shipped that exact bug once already (see ``_migrate``'s own comments), and
it left an issued invoice with no lines on it.
"""


def test_a_price_change_survives_a_store_created_by_an_earlier_build(tmp_path):
    """The columns are added to the existing table, and the row is written whole.

    ``not_before`` and ``note`` are what turns "changed sometime that week, by
    we-do-not-know-who" into a row that reads like an ordinary dated change
    nobody made. Losing them is losing the reason to trust the record.
    """
    import sqlite3

    (tmp_path / "data").mkdir()
    legacy = sqlite3.connect(tmp_path / "data" / "satc_mart.db")
    legacy.executescript(_LEGACY_PRICE_DDL)
    legacy.commit()
    legacy.close()

    change = history.PriceChange(
        kind=history.SERVICE, subject="return_1040", field=history.STANDARD_RATE,
        old_value="450", new_value="495", changed_on=MAR, changed_by=None,
        note="changed outside the app, between 2026-01-05 and 2026-03-10 — "
             "author not recorded",
        not_before=JAN, recorded_at=datetime(2026, 3, 10, 8, 30, 15))

    with SATCStore(tmp_path / "data") as store:
        store.save_price_changes([change])
        reloaded, = store.load_price_changes()

    assert reloaded == change
    assert reloaded.not_before == JAN
    assert reloaded.recorded_at == datetime(2026, 3, 10, 8, 30, 15)
    assert reloaded.changed_by is None
    assert "author not recorded" in reloaded.note


def test_an_authorless_row_does_not_come_back_wearing_a_name(tmp_path):
    """NULL means nobody knows. A loader that turned it into a system actor
    would put a name on the one row whose whole point is that it has none."""
    change = history.PriceChange(
        kind=history.SERVICE, subject="return_1040", field=history.STANDARD_RATE,
        old_value=None, new_value="495", changed_on=MAR, changed_by=None,
        note="changed outside the app", not_before=JAN)

    with SATCStore(tmp_path / "data") as store:
        store.save_price_changes([change])
        reloaded, = store.load_price_changes()

    assert reloaded.changed_by is None
    assert not reloaded.author_is_recorded
    assert reloaded.old_value is None          # not "", not 0
    assert reloaded.old_rate is None


def test_two_rows_never_say_the_same_thing(prices, store):
    """Principle 13. A log the owner learns to scroll past has negative value."""
    history.reconcile_files(store, today=JAN)
    owner_changes_rate(store, prices, old=450, new=495, on=MAR)
    write_rate(prices, 525)
    history.reconcile_files(store, today=JUN)

    summaries = [c.summary() for c in history.all_changes(store)]
    assert len(summaries) == len(set(summaries)) == 2
    assert all(s.strip() for s in summaries)
    assert "author not recorded" in summaries[1]
    assert "human:owner" in summaries[0]
