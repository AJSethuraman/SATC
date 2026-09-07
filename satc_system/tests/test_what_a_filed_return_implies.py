"""Reading a filed return: what it evidences, and what it cannot.

Matter 5 of the 6 September docket. The firm, 5 September:

    "the final invoice is what really should be made after we do the return and
    can actually compute it… I would expect us to be able to feed a final return
    to our software and have it identify the schedules and stuff that we filled
    out and price the engagement at the end and then it would pretty much need
    to ask if there was hourly work and stuff."

Answered *"Build it next"* on 6 September, taking the recommendation to **start
with the read** — the part that carries risk is deciding what a filed return
implies, and it can be built and checked without anything being billed from it.

TWO THINGS THIS MUST NOT DO, and both are tested here rather than trusted to the
module's docstring:

1. **It must not price.** The firm settled ownership on 4 September —
   "client-documents owns the engagement; satc_system holds the return" — and
   #267 put the price on the engagement. A second implementation of the ladder
   here recreates the defect that seam exists to end: two price lists that
   disagree, and the client keeps whichever says the larger number.

2. **It must not produce a finishable invoice.** A return records the RESULT,
   never the hours. `must_ask` is never empty, and `is_complete_enough_to_bill`
   is always False — a stated answer rather than an omission.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.billing.from_return import (
    CANNOT_BE_READ_FROM_A_RETURN,
    SIGNATURES,
    read_return,
    unmatched_units,
)
from satc.models.mart import LineItem, ReturnRecord
from satc.persistence import SATCStore

CLIENT = "SATC-001000"
YEAR = 2025
RK = f"{CLIENT}:{YEAR}:1040:US"


@pytest.fixture()
def store(tmp_path):
    return SATCStore(tmp_path / "store")


def _a_return(store, *lines, filed=False):
    """A return carrying these `(schedule, line_code, label)` line items."""
    mart = store.load_mart()
    mart.returns.append(ReturnRecord(return_key=RK, client_id=CLIENT, tax_year=YEAR,
                                     return_type="1040", jurisdiction="US"))
    for i, (schedule, code, label) in enumerate(lines):
        mart.line_items.append(LineItem(
            line_item_key=f"{RK}:{schedule}:{code}", return_key=RK,
            schedule=schedule, line_code=code, label=label,
            amount=Decimal("1000")))
    store.save_mart(mart)
    return store


# ── the denominator ───────────────────────────────────────────────────────────

def test_an_empty_return_says_it_examined_nothing(store):
    """S2. "No work evidenced" and "nothing was examined" are the same sentence
    otherwise, and only one of them means the job was simple."""
    reading = read_return(store, RK)
    assert reading.read_nothing
    assert reading.line_items_read == 0
    assert not reading.implies
    assert any("not the same as a simple return" in n for n in reading.notes)


def test_a_return_with_content_reports_how_much_it_read(store):
    _a_return(store, ("SCH_C", "1", "Gross receipts"), ("SCH_C", "31", "Net profit"))
    reading = read_return(store, RK)
    assert reading.line_items_read == 2
    assert not reading.read_nothing


# ── what it evidences ─────────────────────────────────────────────────────────

def test_a_schedule_c_return_evidences_schedule_c(store):
    _a_return(store, ("SCH_C", "1", "Gross receipts"), ("SCH_C", "31", "Net profit"))
    reading = read_return(store, RK)

    units = {i.unit for i in reading.implies}
    assert "schedule_c" in units
    implication = next(i for i in reading.implies if i.unit == "schedule_c")
    assert implication.quantity == 1
    assert "2 line item" in implication.because, "the conclusion does not show its work"


def test_three_rental_properties_are_counted_as_three(store):
    """A per-instance unit. The return CAN say how many, and a quote for two
    against a return with three is exactly the conversation this read exists to
    start."""
    _a_return(store,
              ("SCH_E", "A_RENTS", "Rents received — property A"),
              ("SCH_E", "A_DEPR", "Depreciation — property A"),
              ("SCH_E", "B_RENTS", "Rents received — property B"),
              ("SCH_E", "C_RENTS", "Rents received — property C"))
    reading = read_return(store, RK)
    rental = next(i for i in reading.implies if i.unit == "rental")
    assert rental.quantity == 3, "three properties read as one line of rental work"


def test_a_schedule_that_is_not_there_evidences_nothing(store):
    """The control. A read that finds work nobody did is worse than one that
    finds none."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    reading = read_return(store, RK)
    units = {i.unit for i in reading.implies}
    assert "rental" not in units
    assert "farm" not in units


def test_the_evidence_carries_a_sample_so_a_person_can_check_it(store):
    _a_return(store, ("SCH_C", "1", "Gross receipts"), ("SCH_C", "31", "Net profit"))
    evidence = read_return(store, RK).evidence[0]
    assert evidence.line_items == 2
    assert "Gross receipts" in evidence.sample


# ── what it cannot evidence ───────────────────────────────────────────────────

def test_it_always_says_what_it_had_to_leave_out(store):
    """The firm's sentence ends "and stuff". This is the stuff."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    reading = read_return(store, RK)
    keys = {k for k, _ in reading.must_ask}
    assert "hourly" in keys
    assert "records_sorting" in keys
    for _, why in reading.must_ask:
        assert why, "a gap with no explanation is a gap nobody acts on"


def test_the_gaps_are_named_even_on_an_empty_return(store):
    """They are properties of a RETURN, not of this return."""
    assert read_return(store, RK).must_ask


def test_no_reading_is_ever_complete_enough_to_bill(store):
    """A stated answer rather than an omission. A return records the result,
    never the hours, so there is no reading that finishes an invoice."""
    _a_return(store,
              ("SCH_C", "1", "Gross receipts"),
              ("SCH_E", "A_RENTS", "Rents"),
              ("SCH_F", "1", "Farm income"))
    assert not read_return(store, RK).is_complete_enough_to_bill


# ── it reads; it does not price ───────────────────────────────────────────────

def test_the_reading_carries_no_money_of_its_own(store):
    """#267's seam, asserted. Nothing here may name a price: the engagement
    carries the figure the client was quoted, and a second one invented here is
    the defect that seam exists to end."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"),
              ("SCH_E", "A_RENTS", "Rents"))
    reading = read_return(store, RK)

    for implication in reading.implies:
        assert not hasattr(implication, "amount")
        assert not hasattr(implication, "price")
    # and the only money it may show is the quote, read from the engagement
    assert reading.quoted_total == "", "a reading with no ref produced a total"


def test_the_quote_is_read_through_the_ref_not_recomputed(store, tmp_path, monkeypatch):
    """What the client HOLDS, verbatim -- the estimate's own string."""
    import json

    from satc.billing import engagement_price

    ref = "2026-0001"
    (tmp_path / ref).mkdir()
    (tmp_path / ref / "record.json").write_text(json.dumps({
        "EstimateTotal": "$350.00",
        "LineItems": [{"Service": "Simple Filer", "Amount": "$100.00"},
                      {"Service": "Records sorting", "Amount": "$175.00"}],
    }), encoding="utf-8")
    monkeypatch.setenv(engagement_price.ENGAGEMENTS_ENV, str(tmp_path))

    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    reading = read_return(store, RK, engagement_ref=ref)

    assert reading.quoted_total == "$350.00"
    assert ("Records sorting", "$175.00") in reading.quoted_lines
    assert not reading.quote_problem


def test_an_unresolvable_ref_says_why_rather_than_showing_nothing(store, monkeypatch):
    from satc.billing import engagement_price

    monkeypatch.delenv(engagement_price.ENGAGEMENTS_ENV, raising=False)
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    reading = read_return(store, RK, engagement_ref="2026-9999")

    assert reading.quote_problem, "a missing quote passed silently"
    assert reading.quoted_total == ""


# ── filed or not is a finding, not a refusal ──────────────────────────────────

def test_an_unfiled_return_is_read_and_flagged(store):
    """A preparer reviewing before transmitting is doing the right thing. The
    reading just has to say which it is, so a proposal from a draft is never
    mistaken for one from a filed return."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    reading = read_return(store, RK)

    assert not reading.filed
    assert reading.implies, "an unfiled return was refused rather than read"
    assert any("has not been transmitted" in n for n in reading.notes)


# ── the join between the two projects ─────────────────────────────────────────

def test_every_signature_names_a_unit_the_fee_schedule_has():
    """The join is a set of string keys across two projects. A key renamed in
    `fee-schedule.yaml` would otherwise make this module quietly stop evidencing
    that unit — the failure being silence, not an error."""
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[2]
    schedule = root / "client-documents" / "registry" / "fee-schedule.yaml"
    if not schedule.exists():
        pytest.skip("client-documents is not checked out beside satc_system")

    units = set((yaml.safe_load(schedule.read_text(encoding="utf-8")).get("per_unit") or {}))
    assert units, "the fee schedule has no per_unit block; the join moved"

    ours = {s.unit for s in SIGNATURES}
    missing = sorted(ours - units)
    assert not missing, (
        f"these signatures name units the fee schedule no longer has: {missing}")


def test_unmatched_units_reports_what_has_no_signature():
    """Not a failure — a map of where the read stops. A unit nothing accounts
    for is one this module will never evidence, and that should be visible.

    THIS TEST ASSERTED `state_return` WAS UNMATCHED WHEN IT WAS FIRST WRITTEN,
    and it was: the first version of the read looked only at one return's line
    items, and a state return is its own record. `unmatched_units` reporting it
    is what showed the gap — most SATC clients file an Ohio return, so it was the
    most expensive thing the read was missing. It is accounted for now, and this
    test moved with it.
    """
    got = unmatched_units({"schedule_c", "rental", "hourly", "state_return",
                           "local_return", "nonesuch"})
    assert got == ["nonesuch"], got
    for accounted in ("schedule_c", "rental", "hourly", "state_return", "local_return"):
        assert accounted not in got, accounted


def test_the_two_lists_do_not_overlap():
    """A unit cannot be both readable from a return and unreadable from one."""
    readable = {s.unit for s in SIGNATURES}
    unreadable = {k for k, _ in CANNOT_BE_READ_FROM_A_RETURN}
    assert not (readable & unreadable)


# ── state returns, which are read from the SET rather than the content ────────

def _a_state_return(store, jurisdiction, *, with_content=True):
    """A separate ReturnRecord for the same client and year."""
    mart = store.load_mart()
    rk = f"{CLIENT}:{YEAR}:1040:{jurisdiction}"
    mart.returns.append(ReturnRecord(return_key=rk, client_id=CLIENT, tax_year=YEAR,
                                     return_type="1040", jurisdiction=jurisdiction))
    if with_content:
        mart.line_items.append(LineItem(
            line_item_key=f"{rk}:{jurisdiction}:1", return_key=rk,
            schedule=jurisdiction, line_code="1", label=f"{jurisdiction} AGI",
            amount=Decimal("50000")))
    store.save_mart(mart)


def test_an_ohio_return_is_evidenced(store):
    """The commonest priced add-on on the schedule, and it leaves no trace
    inside the federal return's line items — it is its own return record."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    _a_state_return(store, "OH")

    reading = read_return(store, RK)
    state = next(i for i in reading.implies if i.unit == "state_return")
    assert state.quantity == 1
    assert "OH" in state.because


def test_two_states_are_counted_as_two(store):
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    _a_state_return(store, "OH")
    _a_state_return(store, "MI")

    state = next(i for i in read_return(store, RK).implies if i.unit == "state_return")
    assert state.quantity == 2


def test_an_empty_state_return_is_not_billed_for(store):
    """A jurisdiction row with no line items is a return somebody created and
    did not fill in. Charging for it would be charging for a shell."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    _a_state_return(store, "OH", with_content=False)

    assert not [i for i in read_return(store, RK).implies if i.unit == "state_return"]


def test_the_federal_return_does_not_evidence_itself_as_a_state(store):
    """The control. `US` is not a state, and the return being read is not a
    sibling of itself."""
    _a_return(store, ("SCH_C", "1", "Gross receipts"))
    assert not [i for i in read_return(store, RK).implies if i.unit == "state_return"]


def test_k1s_received_are_counted(store):
    _a_return(store,
              ("K1", "A_ORD", "K-1 ordinary business income — Northshore"),
              ("K1", "B_ORD", "K-1 ordinary business income — Beacon Hill"))
    k1 = next(i for i in read_return(store, RK).implies if i.unit == "k1")
    assert k1.quantity == 2


# ── the declared boundary ─────────────────────────────────────────────────────

def test_what_is_deliberately_not_read_carries_its_reason():
    """A boundary, not an oversight. Each entry says why, so somebody deciding
    to close the gap knows what they would have to settle first."""
    from satc.billing.from_return import DELIBERATELY_NOT_READ

    keys = {k for k, _ in DELIBERATELY_NOT_READ}
    assert "local_return" in keys and "owner_k1" in keys
    for _, why in DELIBERATELY_NOT_READ:
        assert len(why) > 30, why


def test_every_priced_unit_is_accounted_for_one_way_or_another():
    """THE PROPERTY THAT MAKES THE READ TRUSTWORTHY. Every `per_unit` key in the
    fee schedule is either read from the return, read from the set of returns,
    named as unreadable from any return, or named as a deliberate boundary.

    Without this, a unit nobody thought about is simply absent from every
    proposal — and absent is indistinguishable from "not applicable to this
    client", which is the confident wrong answer in miniature.
    """
    import pathlib

    import yaml

    root = pathlib.Path(__file__).resolve().parents[2]
    schedule = root / "client-documents" / "registry" / "fee-schedule.yaml"
    if not schedule.exists():
        pytest.skip("client-documents is not checked out beside satc_system")

    units = set((yaml.safe_load(schedule.read_text(encoding="utf-8")).get("per_unit") or {}))
    assert units, "the fee schedule has no per_unit block; the join moved"
    assert unmatched_units(units) == [], (
        "these priced units are neither read nor declared unreadable: "
        f"{unmatched_units(units)}")
