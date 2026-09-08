"""The tie-out is handed in with the answer, and what it did is always said.

THE FIRM, 8 September 2026, correcting a premise rather than a detail:

    "Tie out isn't meant to pass old rules specifically. It's meant to be used
     to prove how a suggestion is correct prior to using it. Like it is handed
     in with the suggestion so the judge can actually assess it."

    "It should state what happened when trying to tie it out. I need info to
     make decisions down the line."

TWO THINGS, AND THE SECOND IS THE ONE THAT WAS MISSING. The proof already rode
on a served answer; nothing said so to the reader, and the one refusal that
exists BECAUSE something was fetched carried the note inside a sentence and
dropped the host, the moment and the digest -- so it could not be re-run by hand.

ALL THREE VERDICTS ARE FINDINGS, which is why silence is reserved for a
different meaning entirely: no line at all means NOBODY ASKED. A rendering that
spoke only on failure would teach a reader that quiet means checked, and quiet
here means not checked, which is the opposite.

AND THE ATTEMPT OUTLIVES THE ANSWER. The decisions the firm named are about
PUBLISHERS -- one unreachable source is a shrug, forty against the same host is
a source to retire -- and none of them can be made from the single answer in
front of somebody. So every attempt is written down, TIED included, and a reader
reports them with what it read them from named.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

import ask as front                                         # noqa: E402
import attempts                                             # noqa: E402
import engine                                               # noqa: E402
import proving                                              # noqa: E402
import record                                               # noqa: E402
import tieouts                                              # noqa: E402
from conftest import DESKS                                  # noqa: E402

DESK = "fixed-assets"
REAL = "https://www.ecfr.gov/current/title-26/section-1.263(a)-2"


class _Page:
    def __init__(self, text, url=""):
        self.text = text
        self.body = text.encode("utf-8")
        self.url = url
        self.at = "2026-09-08T12:00:00+00:00"
        self.nbytes = len(self.body)


def _copy(tmp_path):
    desks = tmp_path / "desks"
    desks.mkdir()
    shutil.copytree(DESKS / DESK, desks / DESK)
    return desks


def _problem(desks):
    desk = record.load(desks / DESK)
    return desk, desk.problems[0]


def _judged(text):
    """A real second reader — every desk requires one (#346). Quotes the text
    the judge is handed, so the engine's containment check really runs."""
    from conftest import a_judgment
    return a_judgment(text)


def _url(desk, citation) -> str:
    """The source's own URL, READ FROM THE RECORD rather than typed here.

    A fixture that claims to have fetched a regulation from a host unrelated to
    the source is asserting something no real transport does -- and would trip
    the landed-host check, which is a different finding wearing this one's
    clothes. `_Page` in `test_an_answer_can_prove_itself.py` carries the same
    warning for the same reason.
    """
    _kind, _obj, source = desk.authority_for(citation)
    return source.url


def _host(url: str) -> str:
    import urllib.parse
    return (urllib.parse.urlsplit(url).hostname or "").removeprefix("www.")


# ── 1. the answer says what the attempt did ─────────────────────────────────

def test_a_tied_answer_says_so_where_the_authority_is(tmp_path):
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    url = _url(desk, p.citation)
    page = _Page(desk.passage(p.citation).text, url=url)
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False, prove=lambda s, c: page,
                       judged=_judged(page.text))
    assert isinstance(out, engine.Served)
    assert out.proof.verdict == proving.TIED
    text = str(out)
    assert "tied out against" in text
    # THE MOMENT AND THE HOST, because "verified" is the record's own word for
    # itself and this rendering exists to escape that.
    assert out.proof.fetched_at in text
    assert _host(url) in text


def test_an_unreachable_publisher_is_said_out_loud_on_the_served_answer(tmp_path):
    """It did NOT withdraw the answer, and the reader still has to be told."""
    desks = _copy(tmp_path)
    desk, p = _problem(desks)

    def dead(source, citation):
        raise OSError("no route to host")

    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False, prove=dead,
                       judged=_judged(desk.passage(p.citation).text))
    assert isinstance(out, engine.Served), "the answer must still stand"
    assert out.proof.verdict == proving.COULD_NOT
    text = str(out)
    assert "NOT TIED OUT" in text
    assert "no route to host" in text
    assert "record alone" in text


def test_no_line_at_all_when_nobody_asked(tmp_path):
    """SILENCE MEANS NOT ASKED FOR, and it is the only thing it may mean.

    Positive precondition first: the answer really was SERVED, so the rendering
    that would carry the line ran at all. Asserting a line's absence on a
    refusal proves nothing about the line.
    """
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False,
                       judged=_judged(desk.passage(p.citation).text))
    assert isinstance(out, engine.Served)
    assert out.proof is None
    text = str(out)
    assert "tied out" not in text and "NOT TIED OUT" not in text


# ── 2. the withdrawal carries its own evidence ──────────────────────────────

def test_a_withdrawal_states_what_the_fetch_did_and_where(tmp_path):
    desks = _copy(tmp_path)
    _desk, p = _problem(desks)
    out = front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                       desks=desks, keep=False,
                       prove=lambda s, c: _Page(
                           f"{p.citation} — this page was rewritten"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_has_moved"
    # THE FIELD, so the refusal can be re-run by hand rather than only read.
    assert out.proof is not None and out.proof.verdict == proving.DIFFERS
    assert out.proof.sha256 and out.proof.fetched_at
    text = str(out)
    assert "NOT TIED OUT" in text
    assert out.desk == DESK, "a refusal that fetched must say which desk did"


# ── 3. what reaches the store, and what may never ───────────────────────────

def test_the_store_keeps_the_publisher_and_never_the_passage():
    """NO VALUES, EVER. This output goes into a repository."""
    secret = "a paragraph of authority nobody outside the record should see"
    p = proving.Proof(proving.TIED, "26 CFR 1.263(a)-2", url=REAL,
                      fetched_at="2026-09-08T12:00:00+00:00",
                      sha256="0" * 64, doc_bytes=len(secret),
                      matched_chars=len(secret))
    line = json.dumps(vars(attempts.from_proof(p, DESK)))
    assert "ecfr.gov" in line and "TIED" in line
    assert secret not in line
    for dropped in ("sha256", "doc_bytes", "matched_chars"):
        assert dropped not in line, f"{dropped} belongs to one answer, not here"


def test_a_note_is_flattened_to_one_line():
    """The note is free text from `proving`. One line, bounded, so a store read
    back as records cannot have a document smuggled through it."""
    p = proving.Proof(proving.COULD_NOT, "x",
                      note="OSError:\n  no route\n\nto host " + "y" * 500)
    note = attempts.from_proof(p).note
    assert "\n" not in note and len(note) <= 300
    assert note.startswith("OSError: no route to host")


def test_an_attempt_survives_a_round_trip(tmp_path):
    path = tmp_path / "attempts.jsonl"
    p = proving.Proof(proving.DIFFERS, "26 CFR 1.263(a)-2", url=REAL,
                      fetched_at="2026-09-08T12:00:00+00:00", note="moved")
    attempts.append(path, attempts.from_proof(p, DESK))
    back = attempts.parse(path.read_text(encoding="utf-8"))
    assert len(back) == 1
    assert back[0].verdict == proving.DIFFERS
    assert back[0].host == "ecfr.gov" and back[0].desk == DESK


def test_a_line_that_will_not_parse_is_counted_rather_than_dropped():
    """One truncated line must not hide every good one -- nor vanish."""
    good = json.dumps({f: "x" for f in attempts.FIELDS})
    text = good + "\n{ truncated\n" + good + "\n"
    assert len(attempts.parse(text)) == 2
    assert attempts.unreadable(text) == 1


# ── 4. it is written on every verdict, and only when keeping ────────────────

@pytest.mark.parametrize("page,verdict", [
    (None, proving.TIED),
    ("{citation} — this page was rewritten", proving.DIFFERS),
])
def test_every_verdict_is_recorded_including_the_one_that_changed_nothing(
        tmp_path, page, verdict):
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    # THE PAGE MUST NAME THE CITATION TO BE A REWRITE. A document that does
    # not is one we cannot show is the right one, which is COULD NOT (#344).
    body = (desk.passage(p.citation).text if page is None
            else page.format(citation=p.citation))
    front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                 desks=desks, keep=True, prove=lambda s, c: _Page(body))
    rows = attempts.parse(
        attempts.store_for(desks, DESK).read_text(encoding="utf-8"))
    assert [r.verdict for r in rows] == [verdict]
    assert rows[0].citation == p.citation


def test_an_unreachable_publisher_is_recorded_too(tmp_path):
    desks = _copy(tmp_path)
    _desk, p = _problem(desks)

    def dead(source, citation):
        raise OSError("no route to host")

    front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                 desks=desks, keep=True, prove=dead)
    rows = attempts.parse(
        attempts.store_for(desks, DESK).read_text(encoding="utf-8"))
    assert [r.verdict for r in rows] == [proving.COULD_NOT]
    assert "no route to host" in rows[0].note


def test_attempts_accumulate_rather_than_replace(tmp_path):
    """A DECISION ABOUT A PUBLISHER IS MADE FROM THE PILE, never from one row.
    A store that overwrote itself would answer the wrong question forever."""
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    for body in (desk.passage(p.citation).text,
                 f"{p.citation} rewritten", f"{p.citation} rewritten again"):
        front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                     desks=desks, keep=True, prove=lambda s, c: _Page(body))
    rows = attempts.parse(
        attempts.store_for(desks, DESK).read_text(encoding="utf-8"))
    assert len(rows) == 3


def test_measuring_writes_nothing(tmp_path):
    """`keep=False` means measuring, and this whole suite passes it. Without
    this the suite would write into the repository on every run."""
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                 desks=desks, keep=False,
                 prove=lambda s, c: _Page(desk.passage(p.citation).text))
    assert not attempts.store_for(desks, DESK).exists()


# ── 5. the reader says what it read ─────────────────────────────────────────

def test_the_report_names_what_it_was_counted_over(tmp_path):
    """`tools/holes.py` printed a zero over one of three stores and the document
    quoting it called the zero a finding. A count says its denominator here."""
    desks = _copy(tmp_path)
    out = tieouts.report(root=desks)
    assert "Read 0 stores of 1 looked for" in out
    assert DESK in out
    assert "nothing has been asked to prove itself yet" in out


def test_the_report_counts_by_publisher_and_shows_only_the_failures(tmp_path):
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    passage = desk.passage(p.citation).text
    url = _url(desk, p.citation)
    for body in (passage, passage, f"{p.citation} rewritten"):
        front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                     desks=desks, keep=True,
                     prove=lambda s, c: _Page(body, url=url))
    out = tieouts.report(root=desks)
    assert "Read 1 store of 1 looked for" in out
    assert "3 attempt(s) recorded" in out
    assert "2  TIED" in out and "1  DIFFERS" in out
    assert f"{_host(url)}: 3" in out
    assert "What happened on the 1 that did not tie out" in out


def test_the_report_says_so_when_every_one_tied_out(tmp_path):
    """A clean result is a finding, and must not render as an empty section."""
    desks = _copy(tmp_path)
    desk, p = _problem(desks)
    front.answer(p.facts, DESK, position=p.answer, citation=p.citation,
                 desks=desks, keep=True,
                 prove=lambda s, c: _Page(desk.passage(p.citation).text))
    out = tieouts.report(root=desks)
    assert "Every one of the 1 tied out. Recorded rather than assumed." in out
