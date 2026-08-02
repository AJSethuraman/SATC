"""The payment ledger's table in the SQLite store of record.

The ledger is where "paid" comes from, so what it forgets on the way to disk is
what the practice cannot answer later: how much arrived, whether this deposit is
already recorded, and HOW we know a payment belongs to an invoice.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from satc.billing.payment import MatchBasis, Method, Payment
from satc.persistence import SATCStore


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
