"""The signing pack, and the rule that makes it worth having.

**A pack with a hole in it is worse than no pack.** The client signs what
arrived and the fourth document turns up later saying something different.
So every document renders, or none of them is written.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cli  # noqa: E402
import intake  # noqa: E402
import packaging  # noqa: E402

SAMPLES = ROOT / "samples"
ENTITY = {"entity_structure": "llc", "entity_state": "Ohio",
          "signer_name": "Priya Raman", "signer_title": "Managing Member",
          # Required of a 1120-S or a 1065 since 26 August 2026, because the
          # letter now states how many K-1s the engagement is scoped for.
          # Ignored for a 1120 -- a C corporation issues none.
          "count_owners": 3,
          "k1_target": "each member's personal return"}


@pytest.fixture
def answers():
    return json.loads((SAMPLES / "interview-answers.json").read_text(encoding="utf-8"))


def _engagement(answers, store, form="1040"):
    extra = {} if form == "1040" else ENTITY
    out = intake.finish(dict(answers) | extra | {"federal_form": form}, store=store)
    assert out.created, out.reason
    return out.ref


def _run(ref, store, out, **kw):
    args = argparse.Namespace(engagement=ref, store=str(store), out=str(out),
                              with_invoice=False, no_pdf=True)
    for k, v in kw.items():
        setattr(args, k, v)
    return cli.cmd_package(args)


# ── which documents ───────────────────────────────────────────────────────

def test_an_individual_signs_the_tax_letter():
    docs = packaging.documents_for({"_return_type": "individual"})
    assert docs == ["tax-letter", "fee-estimate", "onboarding-letter"]


@pytest.mark.parametrize("kind", ["s_corp", "partnership", "c_corp"])
def test_an_entity_signs_an_entity_letter(kind):
    """Never the individual one — which is what happened before 26 August
    2026, when `opening_package` was a hard-coded list that ignored the return
    type entirely and the pack then refused on `TaxpayerName`.

    WHICH entity letter differs. A C corporation gets its own since the same
    day: the business letter's section 02 is entirely about Schedules K-1,
    which a C corporation does not issue, and merging that section's date is
    what made an 1120 pack refuse to render at all.
    """
    expected = {"c_corp": "ccorp-letter"}.get(kind, "business-letter")
    docs = packaging.documents_for({"_return_type": kind})
    assert docs[0] == expected
    assert "tax-letter" not in docs


def test_the_estimate_is_in_every_pack():
    """The firm: "the estimate is required for the engagement to make sense".

    An engagement letter without its estimate asks somebody to sign for work
    at a price they have not been shown.
    """
    for kind in packaging.PACKS:
        assert "fee-estimate" in packaging.documents_for({"_return_type": kind})


def test_the_invoice_is_not_in_the_pack_unless_asked():
    """An invoice is not something a client signs. Off by default so nobody
    sends a bill with a contract by accident."""
    assert "invoice" not in packaging.documents_for({"_return_type": "individual"})
    assert "invoice" in packaging.documents_for({"_return_type": "individual"},
                                                with_invoice=True)


def test_a_record_that_does_not_say_what_it_is_refuses():
    """Guessing here sends an individual engagement letter to a corporation."""
    with pytest.raises(packaging.PackageError) as exc:
        packaging.documents_for({})
    assert "_return_type" in str(exc.value)


def test_an_unknown_engagement_kind_refuses_rather_than_falling_back():
    with pytest.raises(packaging.PackageError) as exc:
        packaging.documents_for({"_return_type": "trust"})
    assert "wrong letter" in str(exc.value)


# ── atomicity ─────────────────────────────────────────────────────────────

def test_a_whole_pack_is_written(answers, tmp_path):
    """Counted against `documents_for`, not against the literal 3.

    It WAS 3, and that was the bug: the demo client has a previous
    accountant, so their pack carries the records release as well, and this
    number said otherwise for as long as `packaging` did not know about the
    conditional attachment. Holding the test to a fixed count is what would
    make sending the attachment by default look like a regression.
    """
    store, out = tmp_path / "store", tmp_path / "pack"
    ref = _engagement(answers, store)
    record = json.loads((store / ref / "record.json").read_text())
    assert _run(ref, store, out) == 0
    names = sorted(p.name for p in out.iterdir())
    assert "MANIFEST.json" in names
    assert sum(n.endswith(".html") for n in names) == \
        len(packaging.documents_for(record))


@pytest.mark.parametrize("form", ["1120S", "1065", "1120"])
def test_every_entity_type_produces_a_pack(answers, tmp_path, form):
    """Including the ones with no sample record of their own."""
    store, out = tmp_path / "store", tmp_path / "pack"
    ref = _engagement(answers, store, form)
    assert _run(ref, store, out) == 0
    # An ENTITY letter, whichever one this entity gets. Naming the file by
    # hand here is what would make a C corporation's own letter look like a
    # regression the day it was added.
    wanted = packaging.documents_for({"_return_type": {"1120S": "s_corp",
                                                       "1065": "partnership",
                                                       "1120": "c_corp"}[form]})[0]
    stem = cli.DOCUMENTS[wanted][1]
    assert any(stem in p.name for p in out.iterdir()), \
        f"a {form} pack should carry {stem!r}"


def test_one_refusal_writes_nothing_at_all(answers, tmp_path):
    """The whole point. Two letters render fine; the estimate does not; the
    client gets nothing rather than two thirds of an agreement."""
    store, out = tmp_path / "store", tmp_path / "pack"
    ref = _engagement(answers, store)
    record = json.loads((store / ref / "record.json").read_text())
    record["EstimateTotal"] = "[CONFIRM: a line cannot be priced]"
    (store / ref / "record.json").write_text(json.dumps(record))

    assert _run(ref, store, out) == 1
    assert not out.exists(), "a refused pack must not leave partial documents"


def test_a_refused_run_does_not_leave_a_STALE_pack_looking_current(answers, tmp_path):
    """FOUND BY TESTING THE REFUSAL PATH, 26 August 2026.

    A refused run left whatever was already in --out untouched, so a complete
    pack for a DIFFERENT engagement sat there looking current. Somebody reads
    "No pack written", opens the folder, finds a full pack, and sends it.
    That is the failure this command exists to prevent, arriving by the back
    door.
    """
    store, out = tmp_path / "store", tmp_path / "pack"
    good = _engagement(answers, store)
    assert _run(good, store, out) == 0

    bad = _engagement(answers, store)
    record = json.loads((store / bad / "record.json").read_text())
    record["EstimateTotal"] = "[CONFIRM: nope]"
    (store / bad / "record.json").write_text(json.dumps(record))

    assert _run(bad, store, out) == 1
    book = json.loads((out / "MANIFEST.json").read_text())
    assert book["EngagementRef"] == good, (
        "the stale pack is still there — which is correct, we must not delete "
        "somebody's work — so the COMMAND has to say so out loud"
    )


def test_a_pack_replaces_a_previous_one_rather_than_merging(answers, tmp_path):
    """An entity pack written over an individual one would leave two
    engagement letters in the folder, and whoever sends it picks the wrong
    one."""
    store, out = tmp_path / "store", tmp_path / "pack"
    assert _run(_engagement(answers, store, "1040"), store, out) == 0
    assert any("SAT-C Engagement Letter" in p.name for p in out.iterdir())

    assert _run(_engagement(answers, store, "1120S"), store, out) == 0
    names = [p.name for p in out.iterdir()]
    assert any("Business Engagement" in n for n in names)
    assert not any(n.startswith("SAT-C Engagement Letter") for n in names), (
        "the individual letter survived into an entity pack"
    )


def test_it_refuses_to_write_into_somebody_elses_folder(answers, tmp_path):
    store, out = tmp_path / "store", tmp_path / "notes"
    out.mkdir()
    (out / "my-notes.txt").write_text("do not delete me")
    ref = _engagement(answers, store)

    assert _run(ref, store, out) == 1
    assert (out / "my-notes.txt").read_text() == "do not delete me"
    assert not (out / "MANIFEST.json").exists()


def test_an_engagement_that_does_not_exist_refuses(tmp_path):
    assert _run("9999-9999", tmp_path / "store", tmp_path / "pack") == 1
    assert not (tmp_path / "pack").exists()


# ── the manifest ──────────────────────────────────────────────────────────

def test_the_manifest_says_what_is_in_the_folder(answers, tmp_path):
    """A folder of PDFs with no note is a folder somebody has to
    reverse-engineer in a year."""
    store, out = tmp_path / "store", tmp_path / "pack"
    ref = _engagement(answers, store)
    assert _run(ref, store, out) == 0

    book = json.loads((out / "MANIFEST.json").read_text())
    assert book["EngagementRef"] == ref
    assert book["EstimateTotal"].startswith("$")
    # The demo client had a previous accountant, so the authorization they
    # sign travels with the letter. It is listed here because the manifest is
    # what somebody reads in a year to know what was sent.
    assert [d["key"] for d in book["Documents"]] == \
        ["tax-letter", "fee-estimate", "onboarding-letter", "records-release"]
    for entry in book["Documents"]:
        assert entry["purpose"], f"{entry['key']} has no stated purpose"
        assert entry["files"], f"{entry['key']} lists no files"


def test_every_document_in_every_pack_has_a_stated_purpose():
    """A key added to PACKS without a PURPOSE would print a blank line in the
    manifest, which is how a folder becomes unexplainable."""
    for kind, docs in packaging.PACKS.items():
        for doc in docs + ["invoice"] + list(packaging.CONDITIONAL):
            assert packaging.PURPOSE.get(doc), f"{doc} ({kind}) has no purpose"


def test_every_document_named_in_a_pack_is_a_real_template():
    for kind, docs in packaging.PACKS.items():
        for doc in docs + list(packaging.CONDITIONAL):
            assert doc in cli.DOCUMENTS, f"{kind} names {doc!r}, which does not exist"
