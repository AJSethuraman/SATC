"""One lead shape, whether it came from the workbook or from a phone call.

The firm, 26 August 2026:

    "the interview has to be set up - so like the questions we ask are based on
     the info we got in the intake lead which is this workbook
     it is possible that a lead has to be input manually though, they may just
     give us contact info"

Two things under test. That a real workbook row survives the trip intact --
including the six keys the interview used to collect and ignore. And that a
lead somebody took by phone is a first-class lead rather than a degraded one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import interview as iv  # noqa: E402
import leads  # noqa: E402

SAMPLES = ROOT / "samples"

# The firm's own export, columns and all — with the PROSPECT MADE UP. The
# shape is real and the person is not: a lead carries a name, an email and a
# phone number, and CLAUDE.md is explicit that none of that belongs in a file
# in this repository. `leads.xlsx` itself is gitignored for the same reason.
#
# Header spelled as the workbook spells it, because that is what the reader
# has to survive.
HEADER = ["Received", "Name", "Email", "Phone", "Location", "Preferred",
          "Services", "Individual complexity", "Business structure",
          "Tax status", "Bookkeeping status", "Urgency", "Deadline", "Notes",
          "Raw JSON", "Lead Number"]

RAW = {
    "services": ["individual_tax", "business_advisory"],
    "individual_complexity": ["w2", "business_owner", "rentals", "multistate"],
    "business_structure": ["sole_prop", "multiple", "not_yet"],
    "business_complexity": ["employees", "multi_location"],
    "revenue_band": "100k_500k",
    "tax_status": "multiple_unfiled",
    "urgency": "soon",
    "notes": "flow test",
    "contact": {"name": "Marcus Ellwood", "email": "mellwood@example.com",
                "phone": "", "preferred": "Email",
                "location": "Westerville, OH", "consent": True},
}

ROW = ["2026-08-14T20:19:20.6404136Z", "Marcus Ellwood",
       "mellwood@example.com", None, "Westerville, OH", "Email",
       "individual_tax, business_advisory",
       "w2, business_owner, rentals, multistate",
       "sole_prop, multiple, not_yet", "multiple_unfiled", None, "soon",
       None, "flow test", json.dumps(RAW), "2026 - 0001"]


# ── the workbook ──────────────────────────────────────────────────────────

def test_a_row_keeps_everything_the_prospect_said():
    """Six of the nine keys were collected by the website, carried into the
    workbook, and read by nothing."""
    lead = leads.from_row(HEADER, ROW)
    for key in ("services", "individual_complexity", "business_structure",
                "business_complexity", "revenue_band", "tax_status",
                "urgency", "notes"):
        assert lead.get(key), f"{key} did not survive the read"
    assert lead["contact"]["email"] == "mellwood@example.com"


def test_the_raw_json_column_wins_over_the_flat_ones():
    """The flat columns are derived from it, and two of them cannot hold what
    it holds -- `business_complexity` and `revenue_band` have no column."""
    lead = leads.from_row(HEADER, ROW)
    assert lead["business_complexity"] == ["employees", "multi_location"]
    assert lead["revenue_band"] == "100k_500k"


def test_a_row_with_no_json_still_reads():
    """A row somebody typed in by hand. Less of it, and what is there is
    honest."""
    row = list(ROW)
    row[HEADER.index("Raw JSON")] = None
    lead = leads.from_row(HEADER, row)
    assert lead["contact"]["name"] == "Marcus Ellwood"
    assert lead["services"] == ["individual_tax", "business_advisory"]
    assert lead["_by_hand"] is True
    assert "revenue_band" not in lead, "a value no column carries was invented"


def test_a_broken_json_cell_is_refused_not_half_read():
    row = list(ROW)
    row[HEADER.index("Raw JSON")] = "{not json"
    with pytest.raises(leads.LeadError, match="Raw JSON"):
        leads.from_row(HEADER, row)


def test_the_lead_number_is_normalised_to_the_ref_spelling():
    """The workbook writes "2026 - 0001"; an engagement ref is "2026-0001",
    and the ref is byte-compared across every document."""
    assert leads.from_row(HEADER, ROW)["_lead_number"] == "2026-0001"


def test_a_comma_string_becomes_a_list_either_way():
    assert leads.normalise({"services": "a, b"})["services"] == ["a", "b"]
    assert leads.normalise({"services": ["a", "b"]})["services"] == ["a", "b"]


# ── by hand ───────────────────────────────────────────────────────────────

def test_a_phone_call_is_a_real_lead():
    lead = leads.by_hand(name="Priya Raman", phone="216-555-0102",
                         notes="Called about last year and this one.")
    assert lead["contact"]["name"] == "Priya Raman"
    assert lead["notes"]
    assert lead["_by_hand"] is True


def test_what_nobody_asked_is_absent_not_none():
    """Absent and "none of these" are different statements. The interview asks
    either way, and a record that says "no rentals" because nobody asked is a
    claim the client never made."""
    lead = leads.by_hand(name="Priya Raman")
    assert "individual_complexity" not in lead
    assert "services" not in lead


@pytest.mark.parametrize("kw", [{"name": "A"}, {"email": "a@b.c"},
                                {"phone": "216-555-0102"}])
def test_any_one_of_the_three_is_enough(kw):
    assert leads.by_hand(**kw)


def test_a_lead_with_nothing_in_it_is_refused():
    with pytest.raises(leads.LeadError, match="nobody to come back to"):
        leads.by_hand(name="  ", email="", phone="")


# ── what a preparer is shown ──────────────────────────────────────────────

def test_the_summary_shows_everything_not_the_three_keys_that_prefill():
    shown = dict(leads.summary(leads.from_row(HEADER, ROW)))
    assert "What they asked for" in shown
    assert "About the business" in shown
    assert "What they wrote" in shown


def test_the_summary_reads_in_the_words_the_client_saw():
    """`individual_tax` is what the form POSTS. "Individual tax preparation"
    is what the prospect clicked, and the labels are read out of the intake
    config rather than copied -- a duplicate list here would drift the way the
    old prefill map did."""
    shown = dict(leads.summary(leads.from_row(HEADER, ROW)))
    assert "Individual tax preparation" in shown["What they asked for"]
    assert "Rental property" in shown["What applies to them"]
    assert "individual_tax" not in shown["What they asked for"]


def test_the_summary_of_a_phone_lead_is_short_and_true():
    shown = dict(leads.summary(leads.by_hand(name="Priya Raman",
                                             phone="216-555-0102")))
    assert set(shown) == {"Name they gave", "Phone"}


# ── the lead reaches the interview ────────────────────────────────────────

def test_the_lead_routes_the_first_question():
    """`services` said individual tax, so the sitting opens on the 1040
    branch rather than blank."""
    lead = leads.from_row(HEADER, ROW)
    q = iv.Interview().question("federal_form")
    assert iv.prefill_for(q, lead) == "1040"


def test_a_lead_asking_for_both_is_not_resolved_for_them():
    """Which entity return a business needs depends on how it is set up.
    There is no answer to give, and it used to offer the individual one."""
    lead = dict(leads.from_row(HEADER, ROW),
                services=["individual_tax", "business_tax"])
    q = iv.Interview().question("federal_form")
    assert iv.prefill_for(q, lead) is None


def test_employees_decide_the_schedule_c_tier():
    """A contractor with staff is not on standard mileage with no payroll,
    and the website already asked."""
    lead = leads.from_row(HEADER, ROW)
    q = iv.Interview().question("schedule_c_kind")
    assert iv.prefill_for(q, lead) == "standard"


def test_a_sole_proprietorship_is_not_offered_as_an_entity_structure():
    """It files on a personal return and has no legal structure of its own.
    Offering one would put it on an engagement letter."""
    lead = leads.from_row(HEADER, ROW)
    assert "sole_prop" in lead["business_structure"]
    q = iv.Interview().question("entity_structure")
    assert iv.prefill_for(q, lead) is None


def test_a_phone_lead_offers_nothing_it_was_not_told():
    lead = leads.by_hand(name="Priya Raman", phone="216-555-0102")
    session = iv.Interview(lead=lead)
    for qid in ("federal_form", "return_features", "schedule_c_kind"):
        assert iv.prefill_for(session.question(qid), lead) is None
