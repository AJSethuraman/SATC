"""One price, and it is the one the client is holding.

**THE PRACTICE HAD TWO PRICE LISTS AND THEY DISAGREED BY 55%.** On identical
facts, 4 September 2026: `client-documents` quoted **$645** from its package
ladder, this catalogue totalled **$1,005** from its per-service rates. Nothing
in either repository said which was the firm's price — and the firm's own
operating procedure had already named the danger, about hand-typed figures:
*"the one the client keeps is the one that says the larger number."*

They were never two numbers for one service. Two pricing **models**: the ladder
bundles (a `starter` 1040 at $100 covers the federal return, the first state,
the first local and the standard deduction) and the catalogue itemises ($450
standing alone, whatever the complexity). $450 and $100 were never comparable,
which is exactly why nobody caught it.

**Two decisions settled it.** *"registry/fee-schedule.yaml is the price"*
(4 September) and *"show the engagement price via the ref"* (5 September). The
second only became possible because the ref acquired a writer the night before.

**WHY A READER AND NOT A PORT.** Reimplementing the ladder here would recreate
the exact problem — two implementations of one price, drifting from the day the
second was written. The figure a client holds is on their estimate, so that is
the one to read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from satc.billing.engagement_price import (
    ENGAGEMENTS_ENV,
    EngagementPrice,
    NoPrice,
    engagements_root,
    price_for_ref,
)


def _record(store: Path, ref: str = "2026-0001", **fields) -> Path:
    """An engagement record shaped like the real one. INVENTED values."""
    body = {"EngagementRef": ref, "ClientFullName": "Walkthrough Fixture",
            "EstimateTotal": "$645.00",
            "LineItems": [{"Service": "Self-Employed", "Amount": "$500.00"},
                          {"Service": "Rental schedule", "Amount": "$145.00"}]}
    body.update(fields)
    d = store / ref
    d.mkdir(parents=True, exist_ok=True)
    p = d / "record.json"
    p.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return p


# ── reading the figure ───────────────────────────────────────────────────────

def test_the_quoted_figure_comes_back_as_the_client_sees_it(tmp_path):
    _record(tmp_path)
    got = price_for_ref("2026-0001", root=tmp_path)
    assert isinstance(got, EngagementPrice)
    assert got.total == "$645.00", (
        "the total is read AS WRITTEN. Re-deriving it from a float here would "
        "be a second rendering of the same money, and the two would eventually "
        "disagree — which is the whole defect this closes")
    assert got.ref == "2026-0001"


def test_the_lines_come_back_too(tmp_path):
    _record(tmp_path)
    got = price_for_ref("2026-0001", root=tmp_path)
    assert ("Self-Employed", "$500.00") in got.lines
    assert ("Rental schedule", "$145.00") in got.lines


def test_the_estimate_beats_a_later_total(tmp_path):
    """`Total` is what an invoice settled at; `EstimateTotal` is what the client
    AGREED to, and a requote is a real event that may move one and not the
    other. A quote screen is about what was agreed."""
    _record(tmp_path, Total="$900.00")
    assert price_for_ref("2026-0001", root=tmp_path).total == "$645.00"


def test_a_record_with_only_a_total_still_answers(tmp_path):
    _record(tmp_path, EstimateTotal="", Total="$720.00")
    assert price_for_ref("2026-0001", root=tmp_path).total == "$720.00"


# ── and every way it can decline ─────────────────────────────────────────────

@pytest.mark.parametrize("ref", ["", "   ", None])
def test_no_ref_says_where_to_record_one(tmp_path, ref):
    got = price_for_ref(ref, root=tmp_path)
    assert isinstance(got, NoPrice) and not got.is_priced
    assert "Engagement ref box" in got.next_step, got.next_step


def test_no_store_configured_names_the_variable(tmp_path, monkeypatch):
    monkeypatch.delenv(ENGAGEMENTS_ENV, raising=False)
    got = price_for_ref("2026-0001")
    assert isinstance(got, NoPrice)
    assert ENGAGEMENTS_ENV in got.next_step


def test_a_missing_record_says_which_path_it_looked_at(tmp_path):
    got = price_for_ref("2026-9999", root=tmp_path)
    assert isinstance(got, NoPrice)
    assert "2026-9999" in got.reason


def test_a_broken_record_does_not_crash_the_screen(tmp_path):
    """A quote screen that dies because a JSON file in another application is
    half-written is worse than one that says the figure could not be read."""
    d = tmp_path / "2026-0001"
    d.mkdir(parents=True)
    (d / "record.json").write_text("{ not json", encoding="utf-8")
    got = price_for_ref("2026-0001", root=tmp_path)
    assert isinstance(got, NoPrice) and "could not be read" in got.reason


def test_an_unpriced_engagement_says_so_rather_than_zero(tmp_path):
    """NEVER $0.00. Nothing priced is not free, and a quote that says otherwise
    is the confident wrong answer this whole system is built against."""
    _record(tmp_path, EstimateTotal="", Total="", Subtotal="")
    got = price_for_ref("2026-0001", root=tmp_path)
    assert isinstance(got, NoPrice)
    assert "not been quoted" in got.next_step or "no priced figure" in got.reason
    assert "0" not in got.reason.replace("2026-0001", "")


def test_the_environment_is_read_when_no_root_is_given(tmp_path, monkeypatch):
    """One export scopes both applications — the same variable
    `client-documents/web.py` reads, so a scratch store points them together."""
    _record(tmp_path)
    monkeypatch.setenv(ENGAGEMENTS_ENV, str(tmp_path))
    assert price_for_ref("2026-0001").total == "$645.00"
    assert engagements_root() == tmp_path


def test_an_explicit_root_beats_the_environment(tmp_path, monkeypatch):
    here = tmp_path / "here"
    there = tmp_path / "there"
    _record(here, EstimateTotal="$111.00")
    _record(there, EstimateTotal="$222.00")
    monkeypatch.setenv(ENGAGEMENTS_ENV, str(there))
    assert price_for_ref("2026-0001", root=here).total == "$111.00"


def test_there_is_no_built_in_guess_at_where_the_engagements_are(monkeypatch):
    """Deliberately no default path. The two applications happen to share a
    machine; guessing at a sibling directory would work on this box and fail
    silently on any other."""
    monkeypatch.delenv(ENGAGEMENTS_ENV, raising=False)
    assert engagements_root() is None


# ── what the quote screen says ───────────────────────────────────────────────

def _quote(tmp_path, ref: str, *, root=None):
    from satc.intake.workflows import load_workflow
    from satc.billing.quote import quote_for
    from satc.models.work import Engagement

    eng = Engagement(client_id="SATC-001000", tax_year=2025)
    eng.engagement_ref = ref
    return quote_for(load_workflow("personal_1040_core"), {},
                     client_id="SATC-001000", tax_year=2025,
                     engagements=[eng], engagements_root=root)


def test_the_quote_carries_the_engagements_own_figure(tmp_path):
    _record(tmp_path)
    q = _quote(tmp_path, "2026-0001", root=tmp_path)
    assert q.engagement_price is not None
    assert q.engagement_price.is_priced
    assert q.engagement_price.total == "$645.00"


def test_a_service_the_ladder_prices_names_the_engagement_and_the_amount(
        tmp_path):
    """THE DECISION, ASSERTED. It used to say "priced by <a file path>", which
    is a reason somebody has to go and look up. Now it says whose figure it is
    and what it is."""
    _record(tmp_path)
    q = _quote(tmp_path, "2026-0001", root=tmp_path)
    said = " ".join(item.reason for item in q.unpriced)
    assert "2026-0001" in said and "$645.00" in said, said


def test_with_no_ref_the_screen_says_how_to_get_the_figure(tmp_path):
    """Silence has to read as silence, with a next step. A blank where a price
    belongs is a field somebody forgot; a sentence is a fact."""
    q = _quote(tmp_path, "", root=tmp_path)
    assert q.engagement_price is not None
    assert not q.engagement_price.is_priced
    assert "Engagement ref box" in q.engagement_price.next_step


def test_this_catalogue_still_does_not_invent_a_second_number(tmp_path):
    """The services the ladder prices must stay OUT of the total, whatever the
    ref does. That is what "one price" means, and it is the half that survives
    even when the engagement cannot be read."""
    _record(tmp_path)
    q = _quote(tmp_path, "2026-0001", root=tmp_path)
    priced_codes = {ln.service_code for ln in q.lines}
    assert "return_1040" not in priced_codes, (
        "this catalogue priced a 1040 again — there are two numbers for one "
        "return, which is the defect")


# ── check the checker ────────────────────────────────────────────────────────

def test_the_two_price_lists_would_still_disagree_if_nothing_had_changed(
        tmp_path):
    """MUTATION, of a sort: the disagreement is real and reproducible.

    If `return_1040` ever loses its `priced_by`, this catalogue prices the
    return again, the two sources come back, and the client keeps whichever
    says more. The evidence is deliberately kept: `standard_rate` is still 450
    in the file, so the size of the gap stays visible while it is reconciled.
    """
    from satc.billing.catalogue import load_services
    svcs = load_services()
    by_code = {s.code: s for s in (svcs.values() if hasattr(svcs, "values")
                                   else svcs)}
    ret = by_code["return_1040"]
    assert ret.priced_by, "return_1040 lost its priced_by; two prices are back"
    assert ret.standard_rate == 450, (
        "the old rate was deleted. It is the evidence of what the two lists "
        "disagreed by, and it is harmless while nothing reads it")


def test_every_service_the_ladder_prices_is_marked(tmp_path):
    """The ladder prices 1040, 1065, 1120S and 1120, plus states, locals,
    rentals, K-1s, brokerage, Schedule C and amendments. Anything of ours in
    that set that is NOT marked is a second price waiting to happen."""
    from satc.billing.catalogue import load_services
    svcs = load_services()
    all_svcs = list(svcs.values() if hasattr(svcs, "values") else svcs)
    unmarked = [s.code for s in all_svcs
                if not s.priced_by and s.unit != "per_hour"]
    assert not unmarked, (
        f"{unmarked} carry their own price and are not per-hour. If the ladder "
        f"prices them too, that is two sources for one figure")
