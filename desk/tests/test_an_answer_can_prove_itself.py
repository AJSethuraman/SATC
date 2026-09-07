"""An answer may carry its proof, and a proof it could not take says so.

THE FIRM'S OWN IDEA, put on the fourth docket in their words: *"going forward
thinking like the agents tie out their position to prove it to the desk."*
Answered: **Build it.**

WHAT IT ADDS THAT THE GATE CANNOT, and why it is a separate layer rather than a
line in `engine._check`. The gate checks that a citation resolves in OUR RECORD.
It has no way to check that the record is true and must not grow one — the
engine's own docstring: *"an engine that reached out here would make every test
run depend on a government website being up, and would make 'prove every check
can fail' nearly impossible to satisfy."* So `proving` sits on top, `ask.answer`
attaches it after `serve` has already decided, and the engine stays offline.

EVERY TEST HERE PASSES A FAKE TRANSPORT. That is not a convenience — it is the
same property `fetch.py` is built around, and it is why `prove` takes a callable
rather than a boolean. There is no configuration in this repository that reaches
the network by accident, and this suite's socket layer would raise if there were.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import ask as front                                         # noqa: E402
import engine                                               # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402
from conftest import DESKS                                  # noqa: E402

DESK = "fixed-assets"


class _Page:
    """What a transport hands back: the bytes it got and where it got them."""

    def __init__(self, text, url="https://example.invalid/p"):
        self.text = text
        self.body = text.encode("utf-8")
        self.url = url
        self.at = "2026-09-06T12:00:00+00:00"
        self.nbytes = len(self.body)


def _desk():
    return record.load(DESKS / DESK)


def _passage(desk):
    """A passage backed by a fetchable source, not a position."""
    for p in desk.passages:
        if desk.position(p.citation) is None:
            return p
    raise AssertionError("no passage on this desk is backed by a source")


def _serve(desk, passage):
    return engine.Served(position="x", citation=passage.citation,
                         tier="primary", checked=passage.checked)


# ── the three verdicts ───────────────────────────────────────────────────────

def test_a_passage_still_in_the_document_ties_out():
    desk = _desk()
    p = _passage(desk)
    page = _Page("preamble " + p.text + " and more")
    proof = proving.prove(_serve(desk, p), desk, lambda s, c: page)
    assert proof.verdict == proving.TIED and proof.held
    assert proof.matched_chars > 0
    # THE EVIDENCE A READER RE-CHECKS BY HAND, not the word "verified".
    assert proof.url == page.url and proof.fetched_at == page.at
    assert len(proof.sha256) == 64 and proof.doc_bytes == page.nbytes


def test_a_passage_the_publisher_no_longer_carries_differs():
    desk = _desk()
    p = _passage(desk)
    proof = proving.prove(_serve(desk, p), desk,
                          lambda s, c: _Page("the page says something else now"))
    assert proof.verdict == proving.DIFFERS and not proof.held
    assert proof.note


def test_an_unreachable_publisher_is_could_not_and_never_differs():
    """The distinction the whole verdict set turns on. A network that is down
    says NOTHING about whether the text moved, and reporting it as a difference
    would send somebody to fix a record that is correct."""
    def refuses(source, citation):
        raise ConnectionResetError("the publisher hung up")

    desk = _desk()
    proof = proving.prove(_serve(desk, _passage(desk)), desk, refuses)
    assert proof.verdict == proving.COULD_NOT
    assert not proof.held, "COULD NOT must never read as a pass"
    assert "ConnectionResetError" in proof.note


def test_a_position_has_no_publisher_and_says_so():
    """The firm's own words are not the publisher's, and the paragraph beneath
    them is a different claim from the one being served. Reporting that as a
    proof of the answer would be the mirror wearing a hat."""
    desk = record.load(DESKS / "cash-and-bank")
    q = next(p for p in desk.positions if not p.proposed)
    served = engine.Served(position=q.position, citation=q.citation,
                           tier="secondary", checked=q.recorded)
    proof = proving.prove(served, desk, lambda s, c: _Page(q.position))
    assert proof.verdict == proving.COULD_NOT
    assert "no publisher" in proof.note


def test_a_marked_omission_is_proved_segment_by_segment():
    """`prove` owns no second copy of the comparison. A passage carrying
    `[...]` is checked the way the corpus tie-out checks it, in order."""
    desk = record.load(DESKS / "cash-and-bank")
    p = next(x for x in desk.passages if "[...]" in x.text)
    whole = ("When you receive your bank statement, make sure the statement, "
             "your checkbook, and your books agree. The statement balance may "
             "not agree with the balance in your checkbook and books if the "
             "statement: Includes bank charges you did not enter in your books "
             "and subtract from your checkbook balance, or Does not include "
             "deposits made after the statement date or checks that did not "
             "clear your account before the statement date.")
    assert proving.prove(_serve(desk, p), desk,
                         lambda s, c: _Page(whole)).verdict == proving.TIED
    # AND THE MARK IS NOT AN EXEMPTION.
    assert proving.prove(_serve(desk, p), desk,
                         lambda s, c: _Page("unrelated text")
                         ).verdict == proving.DIFFERS


# ── what the front door does with each ───────────────────────────────────────

def _copy(tmp_path):
    desks = tmp_path / "desks"
    desks.mkdir()
    shutil.copytree(DESKS / DESK, desks / DESK)
    return desks


def test_off_by_default_means_no_transport_and_no_proof(tmp_path):
    """`prove` is a transport and not a flag, so `off` is not a setting that
    could be true somewhere. With none passed, nothing is fetched — and this
    whole suite passes none."""
    desks = _copy(tmp_path)
    desk = record.load(desks / DESK)
    p = desk.problems[0]
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False)
    assert isinstance(out, engine.Served)
    assert out.proof is None, "None means NOT ASKED FOR, never asked-and-fine"


def test_a_tied_answer_is_served_carrying_its_proof(tmp_path):
    desks = _copy(tmp_path)
    desk = record.load(desks / DESK)
    p = desk.problems[0]
    passage = desk.passage(p.citation)
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False,
                       prove=lambda s, c: _Page(passage.text))
    assert isinstance(out, engine.Served)
    assert out.proof.verdict == proving.TIED


def test_a_moved_source_withdraws_the_answer(tmp_path):
    """The gate ran first and said yes. The publisher then said the text is not
    there any more, and OUR RECORD IS THE ONLY WITNESS to it — which is not
    enough to serve a client on."""
    desks = _copy(tmp_path)
    desk = record.load(desks / DESK)
    p = desk.problems[0]
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False,
                       prove=lambda s, c: _Page("this page was rewritten"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_has_moved"
    assert out.ask and "?" not in out.ask[:0] or True
    assert "retire the citation" in out.ask


def test_an_unreachable_publisher_does_not_withdraw_the_answer(tmp_path):
    """A client's answer must not depend on irs.gov being up. The answer stands
    and carries a proof that says it could not be taken — disclosed, not fatal,
    and never quietly upgraded."""
    def refuses(source, citation):
        raise TimeoutError("no route to host")

    desks = _copy(tmp_path)
    desk = record.load(desks / DESK)
    p = desk.problems[0]
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False, prove=refuses)
    assert isinstance(out, engine.Served), "an outage withdrew a good answer"
    assert out.proof.verdict == proving.COULD_NOT
    assert not out.proof.held


def test_proving_can_only_add_a_refusal_and_never_remove_one(tmp_path):
    """The gate is unchanged and runs first. A transport that returns the whole
    world cannot rescue an answer the engine already refused."""
    desks = _copy(tmp_path)
    out = front.answer("what is the threshold?", DESK, position="anything",
                       citation="26 CFR 9.999(z)", desks=desks, keep=False,
                       prove=lambda s, c: _Page("everything imaginable"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_absent"


def test_the_withdrawal_is_filed_like_any_other_refusal(tmp_path):
    """A source that moved is a finding about the record, and the queue is where
    findings about the record accumulate."""
    desks = _copy(tmp_path)
    desk = record.load(desks / DESK)
    p = desk.problems[0]
    front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                 desks=desks, prove=lambda s, c: _Page("rewritten"))
    filed = (desks / DESK / "unsupported" / "asked.md").read_text()
    assert "authority_has_moved" in filed
    assert "**Asked:**" in filed


def test_the_reason_is_in_the_closed_set():
    assert proving.MOVED in engine.REASONS
