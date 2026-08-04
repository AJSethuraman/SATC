"""What the SQLite store of record forgets on the way to disk.

Two tables, and the same failure in both. The ledger is where "paid" comes from,
so what it drops is what the practice cannot answer later: how much arrived,
whether this deposit is already recorded, and HOW we know a payment belongs to an
invoice. The jobs and tasks tables are where a job's STAGE comes from — the
stage is derived, never stored, so every fact the derivation reads has to
survive the round trip or the derivation answers from a file with holes in it.
"""

from __future__ import annotations

import pytest

import dataclasses
import sqlite3
from datetime import date, datetime
from decimal import Decimal

from satc.billing.payment import MatchBasis, Method, Payment
from satc.persistence import SATCStore


_LEGACY_JOBS_DDL = """
CREATE TABLE jobs (
  job_id TEXT PRIMARY KEY, client_id TEXT, workflow_key TEXT, engagement_type TEXT,
  tax_year INTEGER, period_key TEXT, due_date TEXT, intake_answers TEXT, risk_flags TEXT,
  created_at TEXT, updated_at TEXT);
CREATE TABLE tasks (
  task_id TEXT PRIMARY KEY, job_id TEXT, template_id TEXT, title TEXT, category TEXT,
  audience TEXT, client_request_text TEXT, accepted_alternatives TEXT, why_needed TEXT,
  internal_instructions TEXT, suggested_date TEXT, status TEXT, notes TEXT,
  relationship_generated INTEGER, request_id TEXT, due_date TEXT, waived_reason TEXT,
  follow_up_round INTEGER, completed_by TEXT, completed_at TEXT, procedure TEXT);
"""
"""The jobs and tasks tables exactly as a build before this change created them.

``CREATE TABLE IF NOT EXISTS`` never alters a table that already exists, so this
is what is genuinely on the owner's disk — and a migration that only works on a
database created after the migration was written is not a migration.
"""


def _task(**kw):
    from satc.models.work import Task

    fields = dict(task_id="t-prep", job_id="j-1", template_id="tpl-prep",
                  title="Prepare the 1040", category="prep", audience="internal",
                  status="not_started")
    fields.update(kw)
    return Task(**fields)


def _job(tasks=(), **kw):
    from satc.models.work import Job

    fields = dict(job_id="j-1", client_id="C-100", workflow_key="individual_1040",
                  engagement_type="Individual 1040", tax_year=2025,
                  period_key="2025")
    fields.update(kw)
    return Job(tasks=list(tasks), **fields)


def _deposit(**kw) -> Payment:
    """A plain arrived-money fact, overridable field by field."""
    fields = dict(client_id="C-100", amount=Decimal("450.00"),
                  received_on=date(2026, 3, 14), method=Method.TRANSFER,
                  reference="wire 4471")
    fields.update(kw)
    return Payment(**fields)


def test_a_payment_round_trips_including_basis_and_invoice_id(tmp_path):
    """The basis is the fact most likely to be dropped, and the one that matters.

    A payment that comes back from SQLite having forgotten it was CHOSEN_BY_MODEL
    rather than named by its REFERENCE has lost the only thing that lets a later
    reviewer tell a machine's guess from the bank's own statement — principle 2.
    """
    payment = _deposit(method=Method.CHECK, reference="cheque 8812",
                       invoice_id="INV-2025-C-100",
                       basis=MatchBasis.CHOSEN_BY_MODEL,
                       note="client said this was for the 1040, not the 1120S")
    with SATCStore(tmp_path) as store:
        store.save_payments([payment])

    with SATCStore(tmp_path) as store:      # a fresh process sees exactly this
        loaded, = store.load_payments()

    assert loaded == payment                # every field, not just the ones below
    assert loaded.basis is MatchBasis.CHOSEN_BY_MODEL
    assert loaded.invoice_id == "INV-2025-C-100"
    assert loaded.method is Method.CHECK
    assert loaded.received_on == date(2026, 3, 14)
    assert loaded.payment_id == payment.payment_id


def test_an_unattributed_payment_round_trips_as_unattributed(tmp_path):
    """Empty invoice_id must come back empty, not as some other invoice."""
    with SATCStore(tmp_path) as store:
        store.save_payments([_deposit()])
        loaded, = store.load_payments()
    assert loaded.invoice_id == ""
    assert loaded.basis is MatchBasis.UNMATCHED
    assert not loaded.is_matched


def test_saving_the_same_deposit_twice_leaves_one_row(tmp_path):
    """Re-importing a bank export must not double the practice's revenue.

    payment_id is a content hash of the payment itself, so the second write
    lands on the same primary key. Principle 8: "already recorded" is success.
    """
    payment = _deposit()
    with SATCStore(tmp_path) as store:
        store.save_payments([payment])
        store.save_payments([payment])          # same export, imported again
        rows = store.mart.execute(
            "SELECT COUNT(*) AS n FROM payments").fetchone()["n"]
        ledger = store.load_payments()
    assert rows == 1
    assert [p.amount for p in ledger] == [Decimal("450.00")]


def test_attributing_a_payment_updates_its_row_rather_than_adding_one(tmp_path):
    """Deciding which invoice it was for is not a second deposit."""
    payment = _deposit()
    with SATCStore(tmp_path) as store:
        store.save_payments([payment])
        store.save_payments([payment.against("INV-2025-C-100",
                                             MatchBasis.CHOSEN_BY_HUMAN)])
        ledger = store.load_payments()
    assert len(ledger) == 1
    assert ledger[0].invoice_id == "INV-2025-C-100"
    assert ledger[0].basis is MatchBasis.CHOSEN_BY_HUMAN


def test_a_decimal_amount_survives_exactly(tmp_path):
    """Money is TEXT in and Decimal out. A REAL column would round cents."""
    amounts = {"wire a": Decimal("0.10"), "wire b": Decimal("0.20"),
               "wire c": Decimal("12345.67"), "wire d": Decimal("8675.31")}
    with SATCStore(tmp_path) as store:
        store.save_payments([_deposit(amount=amount, reference=ref)
                             for ref, amount in amounts.items()])
        stored_as = {r[0] for r in store.mart.execute(
            "SELECT typeof(amount) FROM payments")}
        loaded = {p.reference: p.amount for p in store.load_payments()}

    assert stored_as == {"text"}
    assert loaded == amounts
    assert all(isinstance(a, Decimal) for a in loaded.values())
    # Scale survives too: through a float this reads back as "0.1", and a
    # statement line that says $0.1 is a statement the owner has to re-check.
    assert str(loaded["wire a"]) == "0.10"
    # 0.10 + 0.20 is 0.30000000000000004 in float; here it is exact.
    assert sum(loaded.values()) == Decimal("21021.28")


def test_the_unmatched_tray_is_the_payments_nobody_has_attributed(tmp_path):
    """The tray the owner works through, asked for by the database."""
    arrived = _deposit(reference="wire 41")
    attributed = _deposit(amount=Decimal("900.00"), received_on=date(2026, 3, 15),
                          method=Method.CARD, reference="INV-2025-C-100"
                          ).against("INV-2025-C-100", MatchBasis.REFERENCE)
    someone_else = _deposit(client_id="C-200", amount=Decimal("75.00"),
                            received_on=date(2026, 3, 16), method=Method.CASH,
                            reference="counter deposit")
    with SATCStore(tmp_path) as store:
        store.save_payments([arrived, attributed, someone_else])
        tray = store.load_unmatched_payments()
        just_mine = store.load_unmatched_payments("C-100")

    assert [p.payment_id for p in tray] == [arrived.payment_id,
                                            someone_else.payment_id]
    assert [p.payment_id for p in just_mine] == [arrived.payment_id]
    assert all(not p.is_matched for p in tray)


def test_a_payment_pointing_at_a_missing_invoice_still_loads(tmp_path):
    """History always loads. The refusals belong at reconciliation time.

    An attribution to an invoice that is no longer on file is a problem to SHOW
    the owner. Hiding the deposit — or raising on the way past it — would lose
    money that genuinely arrived.
    """
    orphan = _deposit(invoice_id="INV-2019-DELETED", basis=MatchBasis.REFERENCE)
    with SATCStore(tmp_path) as store:
        store.save_payments([orphan])
        assert store.load_invoices() == []       # the invoice really is not there
        loaded, = store.load_payments()

    assert loaded.invoice_id == "INV-2019-DELETED"
    assert loaded.basis is MatchBasis.REFERENCE
    assert loaded.amount == Decimal("450.00")


def test_a_basis_this_build_cannot_read_loads_as_visibly_unmatched(tmp_path):
    """An enum through a database is where this invariant dies quietly.

    An unreadable basis reads back as the WEAKEST claim available rather than
    being invented or raising: the payment lands in the unmatched tray, where a
    human is present to answer it.
    """
    with SATCStore(tmp_path) as store:
        store.save_payments([_deposit(invoice_id="INV-2025-C-100",
                                      basis=MatchBasis.REFERENCE)])
        store.mart.execute("UPDATE payments SET basis=?, method=?",
                           ("chosen_by_some_future_rung", "wampum"))
        store.mart.commit()
        loaded, = store.load_payments()
        tray = store.load_unmatched_payments()

    assert loaded.basis is MatchBasis.UNMATCHED
    assert loaded.method is Method.OTHER
    assert not loaded.is_matched
    assert loaded.invoice_id == "INV-2025-C-100"   # the odd attribution is kept
    assert [p.payment_id for p in tray] == [loaded.payment_id]


# --- jobs and tasks: the facts a stage is derived from ------------------------
#
# Job.stage is a CACHE of what satc.work.stage.derive_stage says, and the store
# deliberately holds no column for it (principle 3 — a stored status lies the
# moment a document arrives). That makes the facts underneath it load-bearing:
# every one of them has to survive a save, or the derivation answers confidently
# from a record with holes in it.


def test_every_recorded_fact_about_a_job_and_its_tasks_survives_a_round_trip(tmp_path):
    """Field by field, from the dataclass itself rather than by hand.

    Written this way on purpose: a hand-listed set of assertions only catches
    the fields somebody thought of, and every one of the three this found —
    obligation_key, blocked_by and escalated_at — was silently dropped for as
    long as the table has existed. Walking ``dataclasses.fields`` means the NEXT
    field added to Job or Task fails here until somebody persists it.
    """
    from satc.models.actor import Actor
    from satc.models.work import Completion

    completed = Completion(by=Actor.owner(), at=datetime(2026, 3, 9, 16, 30),
                           procedure="tied out to the brokerage statement")
    task = _task(
        task_id="t-review", title="Second review", category="review",
        audience="internal", status="blocked", client_request_text="please send",
        accepted_alternatives="a bank letter", why_needed="to tie out interest",
        internal_instructions="check the 1099-INT", due_date=date(2026, 3, 15),
        suggested_date=date(2026, 3, 1), blocked_by=("Prepare the 1040", "Sign off"),
        waived_reason="", follow_up_round=2, escalated_at=date(2026, 2, 20),
        request_id="req-9", completion=completed, notes="second pass",
        relationship_generated=True)
    job = _job([task], obligation_key="C-100|return|1040|US|2025",
               due_date=date(2026, 4, 15), intake_answers={"rental": "yes"},
               risk_flags=["foreign account"], created_at="2026-01-04T09:00:00",
               updated_at="2026-03-09T16:30:00")

    with SATCStore(tmp_path) as store:
        store.save_job(job)
    with SATCStore(tmp_path) as store:          # a fresh process sees exactly this
        loaded, = store.load_jobs()

    dropped = [f.name for f in dataclasses.fields(job)
               if f.name not in ("tasks", "stage")
               and getattr(loaded, f.name) != getattr(job, f.name)]
    assert dropped == [], f"the jobs table forgot {dropped}"

    loaded_task, = loaded.tasks
    dropped = [f.name for f in dataclasses.fields(task)
               if getattr(loaded_task, f.name) != getattr(task, f.name)]
    assert dropped == [], f"the tasks table forgot {dropped}"


def test_the_stage_is_re_derived_from_the_facts_rather_than_restored(tmp_path):
    """The one field deliberately NOT stored, and the reason it does not matter.

    A job saved carrying ``stage='delivered'`` comes back at the default, and
    that is correct: there is no column and there should not be one. What has to
    be true is that asking the derivation about the LOADED job gives the same
    answer as asking it about the one still in memory — which is only possible
    if the tasks underneath came back whole.
    """
    from satc.work.stage import derive_stage

    job = _job([_task(task_id="t1", status="done"),
                _task(task_id="t2", title="Second review", category="review",
                      status="awaiting_review")],
               stage="delivered")             # a stale cache, saved as a lie
    before = derive_stage(job)

    with SATCStore(tmp_path) as store:
        store.save_job(job)
        loaded, = store.load_jobs()

    assert loaded.stage == "not_started", "nothing restores the cache, by design"
    assert before.stage == "in_review"
    assert derive_stage(loaded).stage == before.stage
    assert derive_stage(loaded).why == before.why
    assert derive_stage(loaded).blocked_by == before.blocked_by


def test_a_task_waiting_on_earlier_work_still_says_so_after_a_reload(tmp_path):
    """``blocked_by`` is the fact that separates "waiting on itself" from
    "nobody has picked it up".

    Dropped on the way to disk, a job whose every open task waits on earlier
    work read back as a job where every task is startable — the optimistic
    reading, and the one that lets a return sit while the owner believes it is
    available to pick up.
    """
    from satc.work.stage import derive_stage

    job = _job([_task(task_id="t1", status="done"),
                _task(task_id="t2", title="Assemble the return",
                      status="not_started", blocked_by=("Prepare the 1040",))])
    with SATCStore(tmp_path) as store:
        store.save_job(job)
        loaded, = store.load_jobs()

    assert loaded.tasks[1].blocked_by == ("Prepare the 1040",)
    view = derive_stage(loaded)
    assert view.stage == "in_prep"
    assert view.blocked_by == ("Assemble the return",)
    assert view.next_step == "Finish what they depend on."


def test_a_task_title_containing_a_separator_comes_back_as_one_dependency(tmp_path):
    """``blocked_by`` holds task TITLES, which are free text.

    Stored as a delimited string, "Reconcile interest, dividends and gains"
    splits into two dependencies that do not exist — a fact invented at the
    database boundary, which is where this codebase has lost an invariant
    before.
    """
    job = _job([_task(task_id="t2", status="blocked",
                      blocked_by=("Reconcile interest, dividends and gains",))])
    with SATCStore(tmp_path) as store:
        store.save_job(job)
        loaded, = store.load_jobs()

    assert loaded.tasks[0].blocked_by == ("Reconcile interest, dividends and gains",)


def test_a_store_built_before_these_columns_existed_still_opens_and_saves(tmp_path):
    """The migration has to run against what is actually on the owner's disk.

    ``CREATE TABLE IF NOT EXISTS`` leaves an existing table alone, so a store
    seeded by an older build has the narrow tables above and nothing else will
    add the columns. The legacy row must still load, and a save must land in the
    right columns afterwards.
    """
    legacy = sqlite3.connect(tmp_path / "satc_mart.db")
    legacy.executescript(_LEGACY_JOBS_DDL)
    legacy.execute(
        "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("j-old", "C-100", "individual_1040", "Individual 1040", 2024, "2024",
         "2025-04-15", "{}", "[]", "2025-01-02", "2025-01-02"))
    legacy.commit()
    legacy.close()

    with SATCStore(tmp_path) as store:
        old, = store.load_jobs()
        assert old.job_id == "j-old"
        assert old.obligation_key == ""      # never recorded, so it stays empty
        store.save_job(_job([_task(task_id="t2", status="blocked",
                                   blocked_by=("Prepare the 1040",),
                                   escalated_at=date(2026, 2, 20))],
                            obligation_key="C-100|return|1040|US|2025"))
        fresh = next(j for j in store.load_jobs() if j.job_id == "j-1")

    assert fresh.obligation_key == "C-100|return|1040|US|2025"
    assert fresh.tasks[0].blocked_by == ("Prepare the 1040",)
    assert fresh.tasks[0].escalated_at == date(2026, 2, 20)
    assert fresh.tasks[0].title == "Prepare the 1040"   # nothing shifted a column
    assert fresh.engagement_type == "Individual 1040"


def test_a_migrated_store_ends_up_with_the_same_columns_as_a_fresh_one(tmp_path):
    """The DDL and the migration must not drift apart.

    ``ALTER TABLE`` can only append, so a column added to the MIDDLE of the DDL
    — the natural place to put it, beside the ones it belongs with — lands at
    the end of every database that already exists. Nothing about that fails
    loudly: both stores have the column, both round-trip their own writes, and
    the orders differ only on machines with history on them. This is the check
    that notices, and the reason save_job and _insert_task name their columns
    instead of relying on the order being the same.
    """
    def columns(directory):
        with SATCStore(directory) as store:
            return {table: [r["name"] for r in
                            store.mart.execute(f"PRAGMA table_info({table})")]
                    for table in ("jobs", "tasks")}

    legacy = sqlite3.connect(tmp_path / "satc_mart.db")
    legacy.executescript(_LEGACY_JOBS_DDL)
    legacy.commit()
    legacy.close()

    fresh_dir = tmp_path / "fresh"
    fresh_dir.mkdir()
    assert columns(tmp_path) == columns(fresh_dir)


def test_re_saving_a_job_replaces_its_tasks_rather_than_accumulating_them(tmp_path):
    """Regenerating the interview must not double every task on the job."""
    with SATCStore(tmp_path) as store:
        store.save_job(_job([_task(task_id="t1"), _task(task_id="t2", title="Review")]))
        store.save_job(_job([_task(task_id="t1", status="done")]))
        loaded, = store.load_jobs()

    assert [(t.task_id, t.status) for t in loaded.tasks] == [("t1", "done")]


# --- columns added after a store already existed -----------------------------
#
# CREATE TABLE IF NOT EXISTS never alters an existing table. Two money columns
# were added to the DDL and not to _migrate, which works on every fresh store —
# and every test builds a fresh store, so the suite stayed green while a real
# install broke. A live demo hit it in under a minute: the positional INSERT
# supplied one value too many, invoice_lines refused the write, and an invoice
# was left ISSUED WITH NO LINES.

def _old_schema_store(tmp_path):
    """A store as an earlier build left it: narrower invoice_lines and payments."""
    import sqlite3

    con = sqlite3.connect(tmp_path / "satc_mart.db")
    con.executescript("""
    CREATE TABLE invoice_lines (
      invoice_id TEXT, line_no INTEGER, service_code TEXT, label TEXT,
      quantity TEXT, standard_rate TEXT, note TEXT, performed_on TEXT,
      PRIMARY KEY (invoice_id, line_no));
    CREATE TABLE payments (
      payment_id TEXT PRIMARY KEY, client_id TEXT, amount TEXT, received_on TEXT,
      method TEXT, reference TEXT, invoice_id TEXT, basis TEXT, note TEXT);
    """)
    con.commit()
    con.close()
    from satc.persistence.store import SATCStore
    return SATCStore(tmp_path)


def test_an_invoice_saves_into_a_store_built_by_an_older_build(tmp_path):
    from datetime import date
    from decimal import Decimal

    from satc.billing import Invoice

    store = _old_schema_store(tmp_path)
    inv = Invoice(invoice_id="2026-0001", client_id="CL-1", tax_year=2025)
    inv.add("return_1040", rate_override=Decimal("180"), note="Agreed at signing")
    inv.issue(on=date(2026, 4, 1))
    store.save_invoices([inv])

    back = store.load_invoices("CL-1")[0]
    assert len(back.lines) == 1, "the lines were dropped — the bill is now zero"
    assert back.total == Decimal("180.00")
    assert back.lines[0].rate_adjusted
    assert "Agreed at signing" in back.summary_block()


def test_a_payment_saves_into_a_store_built_by_an_older_build(tmp_path):
    from datetime import date
    from decimal import Decimal

    from satc.billing.payment import Method, Payment

    store = _old_schema_store(tmp_path)
    store.save_payments([Payment(client_id="CL-1", amount=Decimal("450.00"),
                                 received_on=date(2026, 4, 2), method=Method.CHECK,
                                 sequence=1)])
    got = store.load_payments("CL-1")
    assert len(got) == 1
    assert got[0].sequence == 1, "sequence is part of the id — losing it merges payments"


def test_an_invoice_is_never_stored_without_its_lines(tmp_path):
    """They are ONE fact. A half-written invoice is not a partial record, it is
    a wrong one — a bill for zero against work that was done."""
    from datetime import date

    from satc.billing import Invoice
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    inv = Invoice(invoice_id="2026-0002", client_id="CL-1", tax_year=2025)
    inv.add("return_1040")
    inv.issue(on=date(2026, 4, 1))

    # Fail PART WAY THROUGH: the invoice row is written, then the lines raise —
    # which is exactly what a column mismatch did.
    original = store._write_invoices

    def half_write(invoices):
        for one in invoices:
            # Columns NAMED, not positional: this test hand-writes a row, and a
            # positional insert breaks every time the table grows a column.
            store.mart.execute(
                "INSERT OR REPLACE INTO invoices"
                " (invoice_id, client_id, tax_year, plan_key, plan_basis,"
                "  issued_on, due_on, note)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (one.invoice_id, one.client_id, one.tax_year, one.plan_key,
                 one.plan_basis, str(one.issued_on), str(one.due_on), ""))
        raise RuntimeError("simulated schema failure on the lines")

    store._write_invoices = half_write
    try:
        with pytest.raises(RuntimeError):
            store.save_invoices([inv])
    finally:
        store._write_invoices = original

    assert not store.load_invoices("CL-1"), (
        "the invoice header survived a failure that lost its lines")


def test_the_plan_an_invoice_was_issued_on_survives_a_reload(tmp_path):
    """The stamp is worthless if it does not persist — the invoice would come
    back off disk with no plan and fall straight back to the live catalogue."""
    from datetime import date
    from decimal import Decimal

    from satc.billing import Invoice
    from satc.persistence.store import SATCStore

    store = SATCStore(tmp_path)
    inv = Invoice(invoice_id="2026-0001", client_id="CL-1", tax_year=2025,
                  plan_key="household", plan_basis="W-2 household")
    inv.add("return_1040")
    inv.issue(on=date(2026, 3, 1))
    store.save_invoices([inv])

    back = store.load_invoices("CL-1")[0]
    assert back.is_priced
    assert back.plan_discount_pct == Decimal(25)
    assert back.plan_client_label == "Household rate applied"
    assert back.total == inv.total


def test_an_invoice_from_a_store_without_the_plan_columns_still_loads(tmp_path):
    """A record written before the stamp existed never captured one. It falls
    back to the live catalogue — the old behaviour, and the honest answer for a
    record that has nothing else to say."""
    from datetime import date

    from satc.billing import Invoice

    store = _old_schema_store(tmp_path)
    import sqlite3
    con = sqlite3.connect(tmp_path / "satc_mart.db")
    con.execute("DROP TABLE IF EXISTS invoices")
    con.execute("CREATE TABLE invoices (invoice_id TEXT PRIMARY KEY, client_id TEXT,"
                " tax_year INTEGER, plan_key TEXT, plan_basis TEXT, issued_on TEXT,"
                " due_on TEXT, paid_on TEXT, note TEXT)")
    con.execute("INSERT INTO invoices VALUES ('2020-0001','CL-1',2019,'household',"
                "'old record','2020-03-01','2020-04-01',NULL,'')")
    con.commit(); con.close()

    from satc.persistence.store import SATCStore
    fresh = SATCStore(tmp_path)                 # runs _migrate
    back = [i for i in fresh.load_invoices("CL-1") if i.invoice_id == "2020-0001"]
    assert back, "a pre-stamp invoice must still load"
    assert not back[0].is_priced
