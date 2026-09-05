"""A count that shrinks says where the difference went.

D8, FROM THE WALK OF 5 SEPTEMBER 2026. The button read **"Post 10 confirmed"**
and the result read **"posted 6 confirmed values"**.

Nothing was lost -- two W-2s aggregate onto shared 1040 lines, which is exactly
what the mapping table is for. **But the screen never said so**, and the
reviewer's obvious question -- *"which four did not make it?"* -- had no answer
anywhere on the page. A count that shrinks with no explanation is
indistinguishable from a count that lost something, and the difference between
those two matters on a screen whose whole job is to move figures onto a return.

THE FIX IS AN ACCOUNT THAT ADDS UP. Every confirmed value lands in exactly one
bucket, and the buckets sum back to the number the button promised:

    combined        folded into a line with others -- the ordinary case
    workpaper_only  its mapping has no `line_code`, so it feeds the workpaper
                    and is deliberately not posted to the mart
    unmapped        nothing maps its path to a line at all
    no_amount       confirmed without a number, so nothing reached the mart

The last two are the ones worth seeing, and until now all four looked identical
from the outside: a smaller number.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from satc.app.state import AppState
from satc.ingest.extractors.base import make_staged_field
from satc.ingest.staging_gate import LineMapping, StagingGate
from satc.models.staging import StagedDocument
from satc.persistence import SATCStore


def _field(path, label, amount=None, text="", doc="doc-1"):
    f = make_staged_field(
        field_id=f"{doc}:{path}", document_id=doc, client_id="SATC-001000",
        tax_year=2025, field_path=path, label=label,
        raw_value=text or (str(amount) if amount is not None else ""),
        is_money=amount is not None, extractor="test")
    f.status = "CONFIRMED"
    f.confirmed_value_amount = Decimal(str(amount)) if amount is not None else None
    f.confirmed_value_text = text
    return f


def _gate(*fields):
    doc = StagedDocument(document_id="doc-1", client_id="SATC-001000", tax_year=2025,
                         doc_type="W-2", source_path="", fields=list(fields))
    return StagingGate([doc])


WAGES = LineMapping(line_id="wages", paths=["w2.box1_wages"], agg="sum",
                    schedule="1040", line_code="1a", label="Wages")


# ── the account adds up ───────────────────────────────────────────────────────

def test_two_w2s_report_as_one_combined_line_not_as_a_loss():
    """THE DEFECT, in its ordinary form: 2 confirmed -> 1 line."""
    gate = _gate(_field("w2.box1_wages", "Box 1 - Wages", 92400, doc="doc-1"),
                 _field("w2.box1_wages", "Box 1 - Wages", 18000, doc="doc-2"))
    account = gate.posting_account([WAGES])

    assert account["confirmed"] == 2
    assert account["lines"] == 1
    assert len(account["combined"]) == 1
    assert account["combined"][0]["line"] == "Wages"
    assert len(account["combined"][0]["from"]) == 2


def test_a_value_nothing_maps_is_named():
    """The bucket that matters. A document carried a figure and nothing knows
    where to put it -- which used to be indistinguishable from aggregation."""
    gate = _gate(_field("w2.box1_wages", "Box 1 - Wages", 92400),
                 _field("w2.box14_other", "Box 14 - Other", 512))
    account = gate.posting_account([WAGES])

    assert account["unmapped"] == ["Box 14 - Other"]
    assert account["lines"] == 1


def test_a_workpaper_only_mapping_is_named_as_deliberate():
    """Not posted, and that is by design -- so it must not read as a loss."""
    memo = LineMapping(line_id="memo", paths=["w2.box15_state"], kind="text",
                       schedule="1040", line_code="", label="State")
    gate = _gate(_field("w2.box1_wages", "Box 1 - Wages", 92400),
                 _field("w2.box15_state", "Box 15 - State", text="OH"))
    account = gate.posting_account([WAGES, memo])

    assert account["workpaper_only"] == ["Box 15 - State"]
    assert not account["unmapped"], "a mapped field was reported as unmapped"


def test_a_field_confirmed_without_an_amount_is_named():
    gate = _gate(_field("w2.box1_wages", "Box 1 - Wages", 92400, doc="doc-1"),
                 _field("w2.box1_wages", "Box 1 - Wages", None, doc="doc-2"))
    account = gate.posting_account([WAGES])

    assert account["no_amount"] == ["Box 1 - Wages"]
    assert account["lines"] == 1, "the line with a real amount still posted"


def test_every_confirmed_value_lands_in_exactly_one_bucket():
    """THE PROPERTY THE WHOLE FIX RESTS ON. If the buckets do not sum back to
    the number the button promised, the explanation is as untrustworthy as the
    bare count it replaced."""
    memo = LineMapping(line_id="memo", paths=["w2.box15_state"], kind="text",
                       schedule="1040", line_code="", label="State")
    gate = _gate(
        _field("w2.box1_wages", "Box 1 - Wages", 92400, doc="doc-1"),
        _field("w2.box1_wages", "Box 1 - Wages", 18000, doc="doc-2"),
        _field("w2.box15_state", "Box 15 - State", text="OH"),
        _field("w2.box14_other", "Box 14 - Other", 512),
    )
    account = gate.posting_account([WAGES, memo])

    accounted = (sum(len(p["from"]) for p in account["posted"])
                 + len(account["workpaper_only"])
                 + len(account["unmapped"])
                 + len(account["no_amount"]))
    assert accounted == account["confirmed"], account


def test_nothing_confirmed_accounts_for_nothing():
    """The control, and the denominator: an empty gate must not manufacture
    buckets to explain a difference that does not exist."""
    account = _gate().posting_account([WAGES])
    assert account["confirmed"] == 0
    assert account["lines"] == 0
    assert not any(account[k] for k in ("combined", "workpaper_only", "unmapped", "no_amount"))


# ── it reaches the screen ─────────────────────────────────────────────────────

def test_the_client_screen_explains_the_difference(tmp_path, monkeypatch):
    """Asserted on the page, because an account computed and never shown is the
    same defect `opened_today` had -- a number nobody reads."""
    from satc.app.server import create_app

    state = AppState(store=SATCStore(tmp_path / "store"))
    state.posted_summary = {
        "return_key": "rk", "client_id": "SATC-001000", "posted": 1,
        "lines": [("Wages", 110400.0)],
        "account": {"confirmed": 4, "lines": 1,
                    "posted": [{"line": "Wages", "from": ["Box 1 - Wages", "Box 1 - Wages"]}],
                    "combined": [{"line": "Wages", "from": ["Box 1 - Wages", "Box 1 - Wages"]}],
                    "workpaper_only": ["Box 15 - State"],
                    "unmapped": ["Box 14 - Other"], "no_amount": []},
    }
    monkeypatch.setattr("satc.app.server.STATE", state)
    body = create_app().test_client().get("/clients/SATC-001000").get_data(as_text=True)

    assert "4</b> confirmed value(s)" in body, "the promised count is still not on the page"
    assert "combines 2" in body
    assert "Box 14 - Other" in body, "the unmapped value is not named"
    assert "workpaper only" in body
