"""The PII boundary, at the seams where a number actually arrives.

`CLAUDE.md` says: *"Validation tests fail the build if legal names / full TINs
leak into outputs."* Before this file, that was true of `samples/*.json` and of
nothing else -- the shape regex lived in one test and ran over fixtures. The
constraint held because nobody had typed one.

No field can be NAMED for a TIN; `test_registry.py` enforces that and it works.
The leak is free text, which no schema constrains: the interview's working
notes, "what changed since last year", the close-out note a preparer writes
with the filed return open in Drake, and the website's "anything else we should
know?", which lands verbatim in the leads workbook on OneDrive.

The rule these tests hold, above all the others: **no message ever repeats the
value**. A refusal that quotes the number it objected to has written that number
into a terminal, a log and a screenshot -- the leak, one step further along.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import closeout  # noqa: E402
import engagements  # noqa: E402
import presend  # noqa: E402
import tins  # noqa: E402

# Invented, and not a real allocation: 000-prefixed SSNs are never issued.
SSN = "000-12-3456"
EIN = "00-1234567"


# ── the shape ─────────────────────────────────────────────────────────────

def test_it_finds_the_shape_a_person_actually_types():
    assert tins.find(SSN)
    assert tins.find(EIN)
    assert tins.find(f"client said her number is {SSN}, spouse to follow")


@pytest.mark.parametrize("value", [
    "(216) 555-0142",          # a phone number
    "216-555-0142",            # a phone number, dashed
    "2026-08-27",              # a date
    "2026-0001",               # an engagement ref
    "44139-1234",              # ZIP+4
    "$1,234.56",               # money
    "123456789",               # nine bare digits: an account number, a case
                               # reference, a phone typed without punctuation.
                               # Deliberately NOT matched -- see tins.py.
])
def test_it_does_not_fire_on_things_that_are_not_identifiers(value):
    """MEASURED, NOT ASSUMED. Both shapes were run over every rendered
    document, sample, registry and template in the repository -- 302 files,
    zero matches -- before this was allowed to block anything. A guard that
    cries wolf gets muted, and then it is worse than nothing."""
    assert not tins.find(value), value


def test_it_looks_all_the_way_down_a_record():
    """The leak is a free-text answer several levels in, not a top-level
    field -- a top-level field could not be named for a TIN in the first
    place."""
    found = tins.find({"answers": {"notes": f"prior year showed {SSN}"},
                       "states": ["Ohio", f"note: {EIN}"]})
    where = {f.where for f in found}
    assert where == {"answers.notes", "states[1]"}


# ── the value is never repeated ───────────────────────────────────────────

def test_no_refusal_ever_prints_the_number_it_objected_to():
    """The rule this whole module exists under.

    A message quoting the value has put it in a terminal, a log and whatever
    screenshot gets pasted into a ticket. Every message names WHERE, and says
    nothing about WHAT.
    """
    with pytest.raises(tins.TinRefused) as caught:
        tins.refuse({"notes": f"her SSN is {SSN} and the EIN is {EIN}"},
                    "the interview answers")
    said = str(caught.value)
    assert SSN not in said and EIN not in said
    assert "notes" in said, "it must say which answer to fix"
    assert "last four" in said, "it must say what to do instead"


# ── the three seams ───────────────────────────────────────────────────────

def test_the_interview_answers_are_refused_before_they_reach_disk(tmp_path):
    """`engagements/<ref>/interview.json` lives in OneDrive and is read back
    every season."""
    answers = {"client_full_name": "Marcus Ellwood",
               "notes": f"came in with a prior return, {SSN}"}
    with pytest.raises(tins.TinRefused):
        engagements.save_answers(answers, "2026-0001", tmp_path)
    assert not (tmp_path / "2026-0001" / "interview.json").exists(), (
        "the file was written anyway"
    )

    clean = {"client_full_name": "Marcus Ellwood", "notes": "sold a rental"}
    assert engagements.save_answers(clean, "2026-0001", tmp_path).is_file()


def test_the_closeout_record_is_refused_before_it_reaches_disk(tmp_path):
    """The moment of maximum exposure: this is filled in with the filed return
    open on the other screen. `registry/closeout.yaml` says "Nothing is read
    out of Drake" -- that was a comment, and this is the gate."""
    with pytest.raises(tins.TinRefused):
        closeout.save("2026-0001",
                      {"federal_form": "1040",
                       "closeout_note": f"taxpayer {SSN}, spouse elsewhere"},
                      tmp_path)
    assert not (tmp_path / "2026-0001" / "closeout.json").exists()

    ok = closeout.save("2026-0001",
                       {"federal_form": "1040",
                        "closeout_note": "extension was filed in March"},
                       tmp_path)
    assert json.loads(ok.read_text(encoding="utf-8"))["federal_form"] == "1040"


def test_the_gate_blocks_a_pack_that_carries_one(tmp_path):
    """The last mile. A number pasted into the client's name would have
    rendered onto the engagement letter and passed every other check here."""
    (tmp_path / "clean.html").write_text(
        "<html><body><p>Dear Mr. Ellwood, your 2026 return.</p></body></html>",
        encoding="utf-8")
    quiet = presend.no_tin_counted(tmp_path)
    assert not quiet.findings
    assert quiet.examined, "a check that examined nothing is not a pass"

    (tmp_path / "letter.html").write_text(
        f"<html><body><p>Taxpayer {SSN}, entity {EIN}.</p></body></html>",
        encoding="utf-8")
    caught = presend.no_tin_counted(tmp_path)
    assert len(caught.findings) == 2
    assert all(f.blocking for f in caught.findings), (
        "an identifier on a client's document is not an advisory"
    )
    for finding in caught.findings:
        assert SSN not in finding.detail and EIN not in finding.detail


def test_the_gate_runs_this_check_on_a_real_send(tmp_path):
    """S2, the reason two blocking checks once examined nothing on every pack
    ever sent: a check that is not wired into `gate` protects nothing."""
    (tmp_path / "one.html").write_text("<html><body><p>Hello.</p></body></html>",
                                       encoding="utf-8")
    result = presend.gate(tmp_path, {}, skip_render=True)
    assert "no identification number on any page" in result.checked
    examined = dict((what, got.examined) for what, got in result.counts)
    assert examined["no identification number on any page"], (
        "the check ran and looked at nothing"
    )
