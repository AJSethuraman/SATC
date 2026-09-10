"""Verification is the gate: a citation the record has never seen, served.

THE FIRM, 8 September 2026: *"Yes verification is the gate. Who cares if we can
store it outside of it just being quicker the next time. Store if possible sure
but this isn't a limit."*

WHAT THIS REPLACES. `engine._check` refused anything absent from a desk's record,
which made the seven desks a CEILING -- the searcher found the rule, and the
trail stopped at the firm because a source had to be admitted before any desk
could cite it. A candidate is now served if, and only if, the words are on the
publisher's own page right now.

EVERY TEST HERE PASSES A FAKE TRANSPORT, and two of them assert it was NEVER
CALLED. That is the load-bearing half: a check that runs before a fetch is worth
nothing if it merely happens to come first in a function that fetches anyway,
and `conftest.py` replaces the socket layer so nothing here can reach a network
even by accident.

AND THE CONTROL IS AN ACCEPTANCE CRITERION IN ITS OWN RIGHT. With no transport,
no URL or no words, behaviour is byte-identical to before this existed. Without
that, the change is a hole rather than a path.
"""
from __future__ import annotations

import dataclasses
import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask as front                                         # noqa: E402
import attempts                                             # noqa: E402
import candidates                                           # noqa: E402
import domains                                              # noqa: E402
import engine                                               # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                          # noqa: E402

#: A citation NO desk holds. Checked in a test rather than asserted here.
UNHELD = "26 CFR 1.9999-1(z)(4)"
FOUND_AT = "https://www.ecfr.gov/current/title-26/section-1.9999-1"
WORDS = ("Amounts paid to acquire a widget of no recorded description are "
         "capitalized in the year the widget is placed in service.")

#: A tax question and a books question, each classifying cleanly. Both are
#: asserted below rather than trusted, because a fixture that stopped
#: classifying would make every gate test here vacuous.
TAX = "what must a taxpayer capitalize when they acquire equipment?"
BOOKS = "is the leased equipment booked as an asset on the balance sheet?"


class _Page:
    def __init__(self, text, url=""):
        self.text = text
        self.body = text.encode("utf-8")
        self.url = url
        self.at = "2026-09-08T12:00:00+00:00"
        self.nbytes = len(self.body)


class _Counted:
    """A transport that records whether it was ever reached."""

    def __init__(self, page=None, raises=None):
        self.calls = 0
        self.page = page
        self.raises = raises

    def __call__(self, source, citation):
        self.calls += 1
        if self.raises is not None:
            raise self.raises
        return self.page


def _copy(tmp_path):
    """A writable copy of the ONE corpus. `dec-kill` deleted the desks, so there
    is no desk to pick and nothing beneath the record directory."""
    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    return dst


def _ask(desks, question, transport, *, citation=UNHELD, url=FOUND_AT,
         text=WORDS, keep=False, judged=...):
    """A real second reader by default — every desk requires one (#346).

    QUOTING THE WORDS THE ANSWERER HANDED IN, because on this path those words
    are what the fetched page is checked against and what the judge is given.
    A canned quotation would pass the containment check only because the check
    was not running, and every test here would prove nothing.
    """
    from conftest import a_judgment
    if judged is ...:
        judged = a_judgment(text) if text.strip() else None
    return front.answer(question,  position="It is capitalized.",
                        citation=citation, corpus=desks, keep=keep,
                        prove=transport, found_at=url, found_text=text,
                        judged=judged)


# ── the fixtures are real, so a green below is the code and not the setup ────

def test_the_fixtures_are_what_this_file_claims():
    """POSITIVE PRECONDITIONS FOR THE WHOLE FILE. A citation some desk turned
    out to hold, or a question that stopped classifying, would make most of
    these pass for the wrong reason and none of them fail."""
    assert record.load(CORPUS).authority_for(UNHELD) is None, "the corpus holds it"
    tax, books = domains.classify(TAX), domains.classify(BOOKS)
    assert tax and tax.domain.name == "federal-tax"
    assert books and books.domain.name == "us-gaap"
    assert not domains.governs(FOUND_AT, books.domain), (
        "the wrong-body test needs ecfr.gov NOT to settle a books question")
    assert domains.governs(FOUND_AT, tax.domain)


# ── served, on the fetch alone ───────────────────────────────────────────────

def test_a_citation_no_desk_holds_is_served_when_the_words_are_there(tmp_path):
    desks = _copy(tmp_path)
    out = _ask(desks, TAX, lambda s, c: _Page("preamble " + WORDS + " more",
                                              url=FOUND_AT))
    assert isinstance(out, engine.Served), getattr(out, "detail", out)
    assert out.citation == UNHELD
    assert out.proof.verdict == proving.TIED


def test_the_proof_carries_enough_to_re_run_by_hand(tmp_path):
    desks = _copy(tmp_path)
    page = _Page("preamble " + WORDS, url=FOUND_AT)
    out = _ask(desks, TAX, lambda s, c: page)
    assert isinstance(out, engine.Served)
    p = out.proof
    assert p.url == FOUND_AT and p.fetched_at == page.at
    assert len(p.sha256) == 64
    assert p.doc_bytes == page.nbytes
    assert p.matched_chars > 0


def test_the_reader_can_tell_it_from_a_stored_answer(tmp_path):
    """Otherwise it looks identical to one the record holds."""
    desks = _copy(tmp_path)
    out = _ask(desks, TAX, lambda s, c: _Page(WORDS, url=FOUND_AT))
    assert isinstance(out, engine.Served)
    text = str(out)
    assert "NOT FROM THE RECORD" in text
    assert "tied out against" in text and "ecfr.gov" in text
    assert WORDS in text, "the words it rests on must be readable"


def test_a_candidate_is_never_binding_however_good_its_host(tmp_path):
    """THE ISSUE'S OWN CRITERION WAS WRONG AND THIS IS THE CORRECTION.

    #343 said the tier should come from the domain map, on the reasoning that an
    unknown host is tertiary and therefore not binding. True of an unknown host,
    and the common case is not an unknown host: `domains.tier_for` classifies a
    HOST, and irs.gov publishes the regulations AND its own plain-English
    guides, so the map calls it primary while the record calls IRS Pub. 583
    secondary — because a person read that document and saw a guide.

    A candidate is one document nobody has read. `binding` means the firm treats
    it as authority that binds their own work, and the firm has not seen it.
    """
    desks = _copy(tmp_path)
    desk = record.load(desks)
    irs = "https://www.irs.gov/publications/p9999"
    assert domains.tier_for(irs, domains.classify(TAX).domain) == "primary", (
        "if the map stops calling irs.gov primary this test proves nothing")
    out = candidates.consider(
        question=TAX, position="It is capitalized.", citation=UNHELD, url=irs,
        text=WORDS, desk=desk, transport=lambda s, c: _Page(WORDS, url=irs))
    assert isinstance(out, engine.Served)
    assert out.tier == "primary", "the host's tier is still reported"
    assert out.binding is False
    assert out.caveat and "not treated as binding" in out.caveat
    assert "not binding" in str(out)


# ── refused, and each refusal says what happened when trying ────────────────

def test_a_page_without_the_words_refuses(tmp_path):
    desks = _copy(tmp_path)
    out = _ask(desks, TAX, lambda s, c: _Page(
        f"{UNHELD} says something else now", url=FOUND_AT))
    assert isinstance(out, engine.Refusal)
    assert out.reason == proving.MOVED
    assert out.proof is not None and out.proof.verdict == proving.DIFFERS
    assert "NOT TIED OUT" in str(out)


def test_an_unreachable_publisher_refuses_on_this_path(tmp_path):
    """AND THIS IS WHERE THE TWO PATHS DIVERGE. On a stored citation COULD NOT
    still serves, because the record holds the answer. Here the fetch was the
    only thing supporting it."""
    desks = _copy(tmp_path)
    out = _ask(desks, TAX, _Counted(raises=OSError("no route to host")))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_absent"
    assert out.proof is not None and out.proof.verdict == proving.COULD_NOT
    # WHAT HAPPENED WHEN TRYING -- the firm's requirement, in the refusal.
    assert "no route to host" in str(out)
    assert "only about the attempt" in out.detail


def test_COULD_NOT_never_becomes_a_served_answer_here(tmp_path):
    desks = _copy(tmp_path)
    for boom in (OSError("down"), TimeoutError("slow"), ValueError("garbage")):
        out = _ask(desks, TAX, _Counted(raises=boom))
        assert isinstance(out, engine.Refusal), f"{boom!r} served an answer"


# ── the two checks that run BEFORE anything is fetched ──────────────────────

def test_the_wrong_body_of_authority_refuses_without_fetching(tmp_path):
    """Proving that ecfr.gov really says something is not evidence that it gets
    to say it. The transport must never have been called."""
    desks = _copy(tmp_path)
    transport = _Counted(page=_Page(WORDS, url=FOUND_AT))
    out = _ask(desks, BOOKS, transport)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "wrong_body_of_authority"
    assert transport.calls == 0, "it fetched before deciding it may not ask"
    assert "nothing was fetched" in out.detail
    assert "Financial Accounting Standards Board" in out.ask


def test_a_licence_wall_refuses_without_fetching(tmp_path):
    """A wall the firm put up is not routed around by arriving at the same
    publisher through a URL nobody admitted.

    NO DESK HOLDS A `human_only` SOURCE TODAY, so one is constructed — and the
    fact that none exists is asserted, so this test starts failing loudly the
    day one does rather than silently testing a fixture instead of the record.
    """
    desks = _copy(tmp_path)
    desk = record.load(desks)
    assert all(s.readable for s in desk.sources), (
        "a desk now holds an unreadable source; test against the real one")
    walled = record.Source(
        id="ASC", title="FASB Accounting Standards Codification",
        tier="primary", access="human_only", may_store="license_check",
        checked="2026-09-08", citation_prefix="ASC ",
        url="https://asc.fasb.org/")
    desk = dataclasses.replace(desk, sources=desk.sources + (walled,))
    transport = _Counted(page=_Page(WORDS, url="https://asc.fasb.org/842"))

    # A BOOKS QUESTION, so the domain check PASSES and this really reaches the
    # wall. With a tax question `wrong_body_of_authority` fires first and the
    # test would pass while proving nothing about the licence.
    assert domains.governs("https://asc.fasb.org/x",
                           domains.classify(BOOKS).domain)
    out = candidates.consider(
        question=BOOKS, position="x", citation="ASC 842-20-25-1",
        url="https://asc.fasb.org/842-20-25-1", text=WORDS,
        desk=desk, transport=transport)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "source_blocked_by_us"
    assert transport.calls == 0, "it fetched from a source it may never read"
    assert "different door" in out.detail


def test_the_wall_is_matched_on_the_publisher_and_not_the_path(tmp_path):
    desks = _copy(tmp_path)
    desk = record.load(desks)
    walled = record.Source(
        id="ASC", title="FASB ASC", tier="primary", access="human_only",
        may_store="license_check", checked="2026-09-08", citation_prefix="ASC ",
        url="https://asc.fasb.org/")
    desk = dataclasses.replace(desk, sources=desk.sources + (walled,))
    assert candidates.walled("https://asc.fasb.org/anything/at/all", desk)
    assert candidates.walled("https://www.asc.fasb.org/x", desk)
    # AND A LOOKALIKE HOST IS NOT THE WALLED ONE. The boundary is a dot.
    assert candidates.walled("https://notasc.fasb.org/x", desk) is None
    assert candidates.walled(FOUND_AT, desk) is None


# ── the control: nothing changes for anybody who did not ask ────────────────

@pytest.mark.parametrize("kwargs", [
    {"transport": None},
    {"url": ""},
    {"text": ""},
])
def test_without_all_three_the_old_refusal_is_unchanged(tmp_path, kwargs):
    """THE CONTROL THAT STOPS THIS BECOMING A HOLE. A URL with no words is
    nothing to compare; words with no URL are the model's own recollection,
    which is the thing this engine exists not to serve."""
    desks = _copy(tmp_path)
    out = _ask(desks, TAX, kwargs.pop("transport", _Counted(
        page=_Page(WORDS, url=FOUND_AT))), **kwargs)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_absent"
    assert out.proof is None, "nothing was fetched, so there is no attempt"


def test_only_authority_absent_opens_the_candidate_path(tmp_path):
    """Every other refusal is a finding about the question, the client or the
    authority, and a fetch says nothing about any of them. Cited nothing at
    all here, which refuses `no_citation` before the record is consulted."""
    desks = _copy(tmp_path)
    transport = _Counted(page=_Page(WORDS, url=FOUND_AT))
    out = front.answer(TAX,  position="x", citation="", corpus=desks,
                       keep=False, prove=transport, found_at=FOUND_AT,
                       found_text=WORDS)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "no_citation"
    assert transport.calls == 0


# ── and the attempt is kept, like every other ──────────────────────────────

def test_the_attempt_is_recorded_on_this_path_too(tmp_path):
    desks = _copy(tmp_path)
    _ask(desks, TAX, lambda s, c: _Page(WORDS, url=FOUND_AT), keep=True)
    _ask(desks, TAX, _Counted(raises=OSError("down")), keep=True)
    rows = attempts.parse(
        attempts.store_for(desks).read_text(encoding="utf-8"))
    assert [r.verdict for r in rows] == [proving.TIED, proving.COULD_NOT]
    assert all(r.citation == UNHELD for r in rows)


def test_nothing_is_kept_from_the_page_itself(tmp_path):
    """`may_store` is `license_check`: this path caches nothing, so the desk on
    disk must be byte-identical apart from the attempts log."""
    desks = _copy(tmp_path)
    before = {p: p.read_bytes() for p in sorted(desks.rglob("*"))
              if p.is_file()}
    _ask(desks, TAX, lambda s, c: _Page(WORDS, url=FOUND_AT), keep=True)
    after = {p: p.read_bytes() for p in sorted(desks.rglob("*"))
             if p.is_file()}
    added = set(after) - set(before)
    assert added == {attempts.store_for(desks)}, added
    assert all(before[p] == after[p] for p in before), "an existing file moved"
    assert WORDS not in after[attempts.store_for(desks)].decode("utf-8")


def test_the_candidate_source_is_built_and_never_written():
    src = candidates.source_for(FOUND_AT)
    assert src.access == "headless_browser", "the firm's answer on the docket"
    assert src.may_store == "license_check", "nothing is kept"
    assert src.readable
    assert src.url == FOUND_AT
    assert "ecfr.gov" in src.title
