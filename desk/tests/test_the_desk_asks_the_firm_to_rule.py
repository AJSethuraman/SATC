"""The desk asks the firm to rule, and records the answer itself.

26 September 2026. POS7 was found disallowing what its own regulation allows,
and the finding reached the firm the long way: a doer reported it, the session
that builds the desk relayed it in chat. The firm: *"is this not something i
would expect the desk to ask me so it can record the right answer?"* -- and on
which plain words should reach a paragraph: *"why wouldn't the desk send me a
notification asking me to rule on something and record it itself"*.

These tests hold the whole loop on a copy of the corpus: the desk finds what
needs ruling from the record alone, files a proposal the engine has checked,
pushes one line, reads the firm's reply, and writes it into the record -- and
the record still loads, and the finding is not raised again.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import notifying                                            # noqa: E402
import record                                               # noqa: E402
import rulings                                              # noqa: E402
from conftest import CORPUS                                 # noqa: E402

RECORDS = "26 CFR 1.6001-1(a)"
TWELVE = "26 CFR 1.263(a)-4(f)(1)"

#: WHAT THE RECORD SHOWS TODAY, AND IT MAY ONLY SHRINK. Four paragraphs admitted
#: after pilot 3 that the question which asked for each does not reach, and
#: four positions stating a figure the words they rest on do not contain. POS7
#: and POS8 were found by Forge-Occam in pilot 4; POS6 and POS19 were found by
#: this check the first time it ran. Each leaves this list when the firm rules.
#: A NEW entry means somebody admitted a paragraph nothing reaches, or wrote a
#: position whose figure nothing carries -- ask the firm first.
KNOWN = {
    ("reach", RECORDS), ("reach", "26 CFR 1.164-1(a)"),
    ("reach", TWELVE), ("reach", "26 CFR 1.163-8T(a)(3)"),
    ("position", "POS6"), ("position", "POS7"),
    ("position", "POS8"), ("position", "POS19"),
}

MEAL_RATE = ('26 CFR 1.274-12(a)(2) — "the amount allowable as a deduction for '
             'any food or beverage expense described in paragraph (a)(1) of '
             'this section may not exceed 50 percent of the amount of the '
             'expense that otherwise would be allowable."')
DRINK = ('26 CFR 1.274-11(b)(1)(ii) — "the food or beverages are not considered '
         'entertainment if the food or beverages are purchased separately from '
         'the entertainment, or the cost of the food or beverages is stated '
         'separately from the cost of the entertainment"')
POS7_NEW = ("a charge at a bar, brewery or taproom is a food or beverage "
            "expense, deductible at no more than 50 percent, unless the drink "
            "was provided at or during an entertainment activity and was "
            "neither bought nor billed separately from it.\n"
            f"Rests on: {DRINK}\n{MEAL_RATE}")


@pytest.fixture
def corpus(tmp_path):
    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    return dst


@pytest.fixture
def queue(tmp_path):
    return tmp_path / "rulings" / "OPEN.md"


def _found(corpus, kind, subject):
    return next(f for f in rulings.findings(corpus)
                if f.kind == kind and f.subject == subject)


def test_what_needs_ruling_is_read_from_the_record_and_only_shrinks():
    got = {(f.kind, f.subject) for f in rulings.findings(CORPUS)}
    assert got <= KNOWN, f"new findings -- ask the firm first: {got - KNOWN}"


def test_pos7s_rate_is_in_no_word_it_rests_on():
    pos7 = next(q for q in record.load(CORPUS).positions if q.id == "POS7")
    assert rulings.unsupported_figures(pos7) == ("50 percent",)


def test_a_figure_is_the_same_figure_however_it_is_spelt():
    class P:
        position = "deductible at 50% and no more"
        rests_on = (("x", "may not exceed 50 percent of the amount"),)
    assert rulings.unsupported_figures(P) == ()


def test_a_proposal_that_would_not_reach_the_question_is_never_sent(corpus, queue):
    f = _found(corpus, "reach", RECORDS)
    with pytest.raises(ValueError, match="would not bring it up"):
        rulings.ask(f, "mixed account", queue=queue, corpus=corpus)
    assert not queue.exists()


def test_a_reach_ruling_round_trip(corpus, queue):
    f = _found(corpus, "reach", RECORDS)
    entry, line = rulings.ask(f, "commingling; recordkeeping",
                              queue=queue, corpus=corpus, on="2026-09-27")
    assert line.startswith("Desk asks you to rule: ")
    assert line.endswith(f"[{entry.id}]") and len(line) <= notifying.LIMIT

    rid, answer = notifying.reply_in(f"yes [{entry.id}]", sent=line)
    assert rid == entry.id
    done = rulings.settle(queue, rid, answer, on="2026-09-27")
    r = rulings.record_ruling(corpus, done)
    assert r.reaches_on == ("commingling", "recordkeeping")

    assert rulings.load(corpus)[0].subject == RECORDS
    brief = ask.consult(f.asked_by, corpus)
    assert f"### {RECORDS}" in brief
    assert f"the firm ruled it ({entry.id}" in brief
    assert ("reach", RECORDS) not in {
        (x.kind, x.subject) for x in rulings.findings(corpus)}


def test_the_firms_own_words_are_what_is_recorded(corpus, queue):
    f = _found(corpus, "reach", TWELVE)
    entry, line = rulings.ask(f, "subscription", queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(
        f"{entry.id} subscription; twelve months", sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.reaches_on == ("subscription", "twelve months")
    assert f"### {TWELVE}" in ask.consult(f.asked_by, corpus)


def test_no_is_a_ruling_and_is_not_asked_again(corpus, queue):
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    r = rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "no"))
    assert r.outcome == "declined" and r.reaches_on == ()
    assert f"### {RECORDS}" not in ask.consult(f.asked_by, corpus)
    assert ("reach", RECORDS) not in {
        (x.kind, x.subject) for x in rulings.findings(corpus)}


def test_a_ruled_phrase_needs_every_one_of_its_words():
    r = rulings.Ruling(id="R1", kind="reach", subject=RECORDS, ruled="2026-09-27",
                       asked="", reply="yes", reaches_on=("convenience fee",))
    assert rulings.brought_by("a convenience fee on a card", (r,))
    assert not rulings.brought_by("a bank fee", (r,))


def test_a_position_ruling_round_trip(corpus, queue):
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(f"[{entry.id}] Yes", sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer,
                                                     on="2026-09-27"))
    assert r.outcome == "amended"
    pos7 = next(q for q in record.load(corpus).positions if q.id == "POS7")
    assert "neither bought nor billed separately" in pos7.position
    assert pos7.ruled.startswith(f"{entry.id} — 2026-09-27")
    assert rulings.unsupported_figures(pos7) == ()
    assert ("position", "POS7") not in {
        (x.kind, x.subject) for x in rulings.findings(corpus)}


def test_a_proposal_that_still_states_an_unsupported_figure_is_refused(corpus, queue):
    f = _found(corpus, "position", "POS7")
    with pytest.raises(ValueError, match="50 percent"):
        rulings.ask(f, "a brewery charge is a meal at 50 percent.",
                    queue=queue, corpus=corpus)


def test_the_firm_keeping_its_wording_is_recorded_and_ends_the_question(corpus, queue):
    f = _found(corpus, "position", "POS8")
    entry, _ = rulings.ask(f, POS7_NEW.replace("bar, brewery or taproom",
                                               "supermarket"),
                           queue=queue, corpus=corpus)
    before = next(q for q in record.load(corpus).positions if q.id == "POS8")
    r = rulings.record_ruling(corpus, rulings.settle(queue, entry.id,
                                                     "No, keep it"))
    after = next(q for q in record.load(corpus).positions if q.id == "POS8")
    assert r.outcome == "upheld"
    assert after.position == before.position and after.ruled
    assert ("position", "POS8") not in {
        (x.kind, x.subject) for x in rulings.findings(corpus)}


def test_wording_that_would_not_load_is_never_written(corpus, queue):
    """The firm's own words go through the same check as the desk's."""
    f = _found(corpus, "position", "POS7")
    entry, _ = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    done = rulings.settle(queue, entry.id, "a brewery charge is always 80% deductible")
    before = (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="80%"):
        rulings.record_ruling(corpus, done)
    assert (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8") == before
    assert not (corpus / rulings.RULINGS_FILE).exists()


def test_one_open_ruling_per_subject(corpus, queue):
    f = _found(corpus, "reach", RECORDS)
    rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    with pytest.raises(ValueError, match="already waiting"):
        rulings.ask(f, "recordkeeping", queue=queue, corpus=corpus)


def test_an_admission_must_name_a_paragraph_its_source_holds(corpus):
    s = (corpus / "SOURCES.md").read_text(encoding="utf-8")
    (corpus / "SOURCES.md").write_text(
        s.replace("**Admitted for:** 26 CFR 1.6001-1(a) —",
                  "**Admitted for:** 26 CFR 1.6001-1(z) —"), encoding="utf-8")
    with pytest.raises(record.RecordError, match="does not hold"):
        record.load(corpus)


@pytest.mark.parametrize("reply", ["No, make it 60 percent", "yes but only for bars"])
def test_a_yes_or_no_that_goes_on_to_say_more_is_asked_again(corpus, queue, reply):
    """ "No, make it 60%" is not a no. Recording either reading is a guess."""
    f = _found(corpus, "position", "POS7")
    entry, _ = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, entry.id, reply))
    assert not (corpus / rulings.RULINGS_FILE).exists()


def test_a_wording_only_proposal_keeps_what_the_position_rests_on(corpus, queue):
    f = _found(corpus, "position", "POS8")
    before = next(q for q in record.load(corpus).positions if q.id == "POS8")
    wording = before.position.replace("100 percent only", "fully deductible only")
    entry, _ = rulings.ask(f, wording, queue=queue, corpus=corpus)
    rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "yes"))
    after = next(q for q in record.load(corpus).positions if q.id == "POS8")
    assert after.rests_on == before.rests_on
    assert "fully deductible only" in after.position


def test_a_ruled_word_the_law_never_uses_still_brings_the_paragraph(corpus, queue):
    """Codex on #401: a question whose only substantive word is the ruled one
    reaches NOTHING by overlap -- the exact mismatch rulings exist to repair --
    and `consult` returned "Nothing on file" before the rulings were read."""
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "yes"))
    assert not ask.looked("commingling?", corpus)
    got = ask.consult("commingling?", corpus)
    assert f"### {RECORDS}" in got
    assert "Nothing on file" not in got


def test_the_firms_own_words_must_reach_the_question_too(corpus, queue):
    """Codex on #401: words that would never bring the paragraph up for the
    question that missed it were recorded, and the finding was then suppressed
    as ruled. They are refused and the ruling stays open."""
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    done = rulings.settle(queue, entry.id, "books of account")
    with pytest.raises(ValueError, match="would not bring it up"):
        rulings.record_ruling(corpus, done)
    assert not (corpus / rulings.RULINGS_FILE).exists()
    assert ("reach", RECORDS) in {
        (x.kind, x.subject) for x in rulings.findings(corpus)}


def test_the_live_front_door_honours_a_ruling_too(corpus, queue, tmp_path):
    """Codex on #401: `consult_or_file` asked only the pool, so a question the
    firm's ruling answered was filed as a hole in the authority it points at."""
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "yes"))
    parked = tmp_path / "unfiled" / "CLOSE.md"
    got, filed = ask.consult_or_file("commingling?", queue=parked, corpus=corpus)
    assert filed is None and not parked.exists()
    assert f"### {RECORDS}" in got


@pytest.mark.parametrize("reply", ["R1 yes", "yes [R1]", "[R1] Yes."])
def test_a_plain_yes_survives_a_question_that_says_yes(corpus, queue, reply):
    """The ruling's own line says "Reply yes ... no to keep it", and the old
    echo filter deleted each of its words from the reply wherever they stood:
    a plain "R1 yes" came back as nothing at all."""
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    assert entry.id == "R1"
    rid, answer = notifying.reply_in(reply, sent=line)
    assert rid == "R1"
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.outcome == "amended"


def test_the_notification_quoted_back_with_a_yes_is_a_yes(corpus, queue):
    """Codex on #401: tapping the push quotes it, and the quote made a yes
    read as the firm's own words."""
    f = _found(corpus, "reach", RECORDS)
    entry, line = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(line + " — yes", sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.reaches_on == ("commingling",)
    assert r.reply == line + " — yes"


def test_the_firms_wording_is_kept_as_they_typed_it():
    line = notifying.line("POS7 states 50 percent. Reply yes, no, or your own",
                          ref="R2", verb="Desk asks you to rule")
    assert notifying.added(line + " — Bars only, at 50%.", line) == \
        "Bars only, at 50%"


def test_a_parked_reply_may_reuse_a_word_of_the_question():
    """The same filter ate "U1 gross receipts" answering "are unidentified
    deposits gross receipts?"."""
    e = notifying.line("are unidentified deposits gross receipts?", ref="U1")
    assert notifying.reply_in("U1 gross receipts", sent=e) == (
        "U1", "U1 gross receipts")


def test_the_brief_does_not_say_escalate_on_anything_not_printed():
    """Codex on #401: the old line told an answerer to escalate whenever the
    rule was not printed -- the rank-442 case the shelf exists to fix."""
    got = ask.consult("A single account carries purchases for customers' jobs "
                      "and for the household. What records must be kept?")
    assert "NOT printed here, do not cite it from" not in got
    assert "not in a section the list shows once you have read it" in got


def test_a_long_reply_sharing_words_with_the_question_is_kept_whole():
    """The echo is cut only where the WHOLE run appears. A reply longer than
    the question, sharing some of its words out of order, loses nothing."""
    e = notifying.line("are unidentified deposits gross receipts?", ref="U1")
    reply = ("U1 gross receipts only where the deposits trace to customers; "
             "unidentified ones stay open")
    assert notifying.added(reply, e) == reply[3:]


@pytest.mark.parametrize("reply", ["R1 yes, keep it", "R1 yes no", "R1 no yes",
                                   "R1 keep it, yes"])
def test_a_reply_that_says_both_is_asked_again(corpus, queue, reply):
    """Codex on #401: "yes, keep it" read as yes and changed the position,
    though "keep it" is the no. A reply carrying both decisions is refused."""
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))


@pytest.mark.parametrize("reply", ["R1 no, keep it", "R1 no - leave it as is",
                                   "R1 yes please, looks good"])
def test_one_decision_said_twice_is_still_one_decision(corpus, queue, reply):
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.outcome in ("amended", "upheld")


def test_a_running_desk_serves_the_ruled_wording_at_once(corpus, queue):
    """Codex on #401: `findings` loads the corpus into `ask`'s cache, the
    ruling rewrote POSITIONS.md, and the same process went on serving the
    wording the firm had just corrected."""
    f = _found(corpus, "position", "POS7")
    ask._corpus(corpus)                       # warm the cache, as a live desk has
    entry, _ = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "yes"))
    pos7 = next(q for q in ask._corpus(corpus)[0].positions if q.id == "POS7")
    assert "neither bought nor billed separately" in pos7.position
