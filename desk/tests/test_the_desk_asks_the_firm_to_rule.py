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
        f'{entry.id} "subscription; twelve months"', sent=line)
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
    done = rulings.settle(queue, entry.id,
                          '"a brewery charge is always 80% deductible"')
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
    done = rulings.settle(queue, entry.id, '"books of account"')
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


def test_a_ruling_for_one_question_does_not_silence_another(corpus, queue):
    """Codex on #401: a second question admitted for the same paragraph was
    suppressed by a ruling that never fires for it."""
    s = (corpus / "SOURCES.md").read_text(encoding="utf-8")
    other = "A sole trader keeps no ledger at all. What must they hold onto?"
    s = s.replace('**Admitted for:** 26 CFR 1.6001-1(a) — "',
                  f'**Admitted for:** 26 CFR 1.6001-1(a) — "{other}"\n'
                  '26 CFR 1.6001-1(a) — "', 1)
    (corpus / "SOURCES.md").write_text(s, encoding="utf-8")
    first = next(f for f in rulings.findings(corpus)
                 if f.subject == RECORDS and "commingling" in f.asked_by)
    entry, _ = rulings.ask(first, "commingling", queue=queue, corpus=corpus)
    rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "yes"))
    assert RECORDS not in {f.held.citation for f in ask.looked(other, corpus)}
    left = [f.asked_by for f in rulings.findings(corpus) if f.subject == RECORDS]
    assert left == [other]


def test_recording_a_ruling_twice_changes_nothing(corpus, queue):
    """Codex on #401: a retry appended the same R<n> again, and the next load
    of the rulings raised -- taking every consultation down with it."""
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    done = rulings.settle(queue, entry.id, "yes")
    first = rulings.record_ruling(corpus, done)
    text = (corpus / rulings.RULINGS_FILE).read_text(encoding="utf-8")
    again = rulings.record_ruling(corpus, done)
    assert again == first
    assert (corpus / rulings.RULINGS_FILE).read_text(encoding="utf-8") == text
    assert len(rulings.load(corpus)) == 1


@pytest.mark.parametrize("figure", ["a 36-month lease", "a 12-day period",
                                    "a 50-percent limit"])
def test_a_hyphenated_figure_is_still_a_figure(figure):
    """Codex on #401: "36-month lease" slipped past the figure check, so a
    proposal could state an unsupported duration and be recorded as ruled."""
    class P:
        position = f"deductible over {figure}"
        rests_on = (("x", "no figure here at all"),)
    assert rulings.unsupported_figures(P)


def test_a_different_ruling_under_a_used_number_is_refused(corpus, queue):
    """Codex on #401: an id already on record was taken as a retry and the
    firm's NEW answer silently discarded, when it was a different ruling that
    happened to be numbered the same."""
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    rulings.record_ruling(corpus, rulings.settle(queue, entry.id, "yes"))
    other = rulings.Asked(id=entry.id, kind="position", subject="POS7",
                          why="x", proposed=POS7_NEW, recorded="2026-09-27",
                          answer="yes", answered="2026-09-27")
    with pytest.raises(record.RecordError, match="already records a different"):
        rulings.record_ruling(corpus, other)


@pytest.mark.parametrize("wording", [
    "a charge at a bar is a meal.\n\n**Needs:** taxpayer",
    "a charge at a bar is a meal. **Unless:** trade",
])
def test_wording_cannot_carry_a_field_of_the_position(corpus, queue, wording):
    """Codex on #401: a "**Needs:** taxpayer" line in proposed wording became
    real metadata -- a client-fact gate nobody ruled on."""
    f = _found(corpus, "position", "POS7")
    with pytest.raises(ValueError, match="field"):
        rulings.ask(f, wording, queue=queue, corpus=corpus)


def test_the_same_number_with_a_different_proposal_is_not_a_retry(corpus, queue):
    """Codex on #401: two queues numbering R1 for the same finding, both
    answered yes, but proposing different words -- the second was returned
    as the first."""
    f = _found(corpus, "reach", RECORDS)
    entry, _ = rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    done = rulings.settle(queue, entry.id, "yes")
    rulings.record_ruling(corpus, done)
    import dataclasses
    other = dataclasses.replace(done, proposed="recordkeeping")
    with pytest.raises(record.RecordError, match="already records a different"):
        rulings.record_ruling(corpus, other)


@pytest.mark.parametrize("reply", ["R1 Sounds good", "R1 I agree",
                                   "R1 Please keep it", "R1 Don't change it"])
def test_a_courtesy_is_not_new_wording(corpus, queue, reply):
    """Independent review of #401: "Sounds good" to POS7's ruling became
    POS7's wording. A reply too short to be a position is asked again."""
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    before = (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("pid", ["POS1", "POS2", "POS10", "POS13"])
def test_a_ruling_changes_the_wording_and_rests_on_and_nothing_else(corpus, pid):
    """Independent review of #401: new rests-on words dropped every field
    between Position and Why -- Needs, Unless, Default -- and could leave the
    position unratified."""
    before = next(q for q in record.load(corpus).positions if q.id == pid)
    rests = "; ".join(f'{c} — "{w}"' if c != before.citation else f'"{w}"'
                      for c, w in before.rests_on)
    rests = "\n".join(f'{c} — "{w}"' for c, w in before.rests_on)
    rulings._amended(corpus, pid, before.position + " (ruled)", rests,
                     ruled="R9 — 2026-09-27: \"yes\"")
    after = next(q for q in record.load(corpus).positions if q.id == pid)
    assert after.position.endswith("(ruled)")
    for field in ("needs", "unless", "default", "ratified", "kind", "applies_at"):
        assert getattr(after, field) == getattr(before, field), (pid, field)
    assert after.rests_on == before.rests_on


@pytest.mark.parametrize("pid", ["POS13", "POS14"])
def test_keeping_a_position_leaves_its_ratified_line_whole(corpus, pid):
    """Independent review of #401: Ratified wraps over two lines on POS13 and
    POS14, and `Ruled:` was spliced in after the first."""
    before = next(q for q in record.load(corpus).positions if q.id == pid)
    rulings._mark_upheld(corpus, pid, 'R9 — 2026-09-27: "no"')
    after = next(q for q in record.load(corpus).positions if q.id == pid)
    assert after.ruled == 'R9 — 2026-09-27: "no"'
    assert after.ratified == before.ratified


def test_a_ruling_that_cannot_be_sent_is_not_filed(corpus, queue, monkeypatch):
    """Independent review of #401: the queue was written before the line was
    built, so a line the PII guard refused left the subject "already waiting"
    with nothing sent."""
    f = _found(corpus, "reach", RECORDS)
    def refuse(*a, **k):
        raise ValueError("refusing to send this notification")
    monkeypatch.setattr(notifying, "line", refuse)
    with pytest.raises(ValueError, match="refusing"):
        rulings.ask(f, "commingling", queue=queue, corpus=corpus)
    assert not queue.exists()


# ------------------------------------------ second independent review of #401


@pytest.mark.parametrize("reply", [
    "R1 Please leave the current wording alone, it is correct as written",
    "R1 That looks right to me, go ahead and record the desk's wording"])
def test_a_long_reply_is_not_wording_unless_it_is_quoted(corpus, queue, reply):
    """Second independent review of #401: both of these became POS7's text.
    The first means no and the second yes, and no length or figure check can
    tell a sentence ABOUT the wording from the wording. So the firm's own
    wording is what they put in quotes, and anything else is asked again."""
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    before = (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("open_, close", [('"', '"'), ("“", "”"),
                                           ("'", "'"), ("‘", "’")])
def test_quoted_wording_is_the_firms_wording(corpus, queue, open_, close):
    wording = POS7_NEW.split("\n")[0].replace("a charge at", "any charge at")
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(f"R1 {open_}{wording}{close}", sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.outcome == "amended"
    pos7 = next(q for q in record.load(corpus).positions if q.id == "POS7")
    assert pos7.position.startswith("any charge at a bar")
    assert open_ not in pos7.position and close not in pos7.position


def test_the_line_says_how_to_send_wording(corpus, queue):
    f = _found(corpus, "position", "POS7")
    _, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    assert "in quotes" in line
    g = _found(corpus, "reach", RECORDS)
    _, line = rulings.ask(g, "commingling", queue=queue, corpus=corpus)
    assert "in quotes" in line


@pytest.mark.parametrize("reply", ["R1 No, go ahead", "R1 No, that looks good",
                                   "R1 no, sounds fine", "R1 yes, leave it"])
def test_an_approval_word_is_not_filler_after_a_no(corpus, queue, reply):
    """Second independent review of #401: "No, go ahead" was recorded as the
    firm keeping its wording -- "go", "ahead", "looks", "good", "fine" and
    "sounds" were filler. Each most likely means "no objection"."""
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))


def test_a_retry_after_the_position_was_written_rules_it_once(corpus, queue,
                                                             monkeypatch):
    """Second independent review of #401: POSITIONS.md written, RULINGS.md
    not (a crash between the two), and the retry added a second `Ruled:`."""
    f = _found(corpus, "position", "POS7")
    entry, _ = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    done = rulings.settle(queue, entry.id, "yes")
    real = rulings._append_ruling

    def crash(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(rulings, "_append_ruling", crash)
    with pytest.raises(OSError):
        rulings.record_ruling(corpus, done)
    monkeypatch.setattr(rulings, "_append_ruling", real)
    rulings.record_ruling(corpus, done)
    text = (corpus / "positions" / "POSITIONS.md").read_text(encoding="utf-8")
    assert text.count(f"**Ruled:** {entry.id} ") == 1
    record.load(corpus)


def test_a_date_that_would_not_load_is_refused_when_settled(corpus, queue):
    f = _found(corpus, "position", "POS7")
    entry, _ = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    with pytest.raises(record.RecordError, match="date"):
        rulings.settle(queue, entry.id, "yes", on="27/09/2026")
    assert not rulings.queued(queue)[0].answered


# ------------------------------------------- third independent review of #401


@pytest.mark.parametrize("on", ["20260927", "2026-W39-6", "2026-9-27"])
def test_only_the_date_the_record_can_read_is_accepted(corpus, queue, on):
    """Third independent review: `date.fromisoformat` also takes the compact
    and week forms, the RULINGS.md parser does not, and every consultation
    then failed to load."""
    f = _found(corpus, "position", "POS7")
    entry, _ = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    with pytest.raises(record.RecordError, match="date"):
        rulings.settle(queue, entry.id, "yes", on=on)


@pytest.mark.parametrize("reply", ["R1 No, do it", "R1 no please do",
                                   "R1 no, do that"])
def test_do_it_is_not_filler_after_a_no(corpus, queue, reply):
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))


def test_yes_do_it_is_still_a_yes(corpus, queue):
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in("R1 yes, do it", sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.outcome == "amended"


@pytest.mark.parametrize("reply", ['R1 "subscription"; "twelve months"',
                                   'R1 "subscription" and "twelve months"',
                                   'R1 “subscription”, “twelve months”'])
def test_several_quoted_phrases_are_several_phrases(corpus, queue, reply):
    """Third independent review: everything from the first quote to the last
    was one phrase, and stray quote marks were written to the record."""
    f = _found(corpus, "reach", TWELVE)
    entry, line = rulings.ask(f, "subscription", queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    r = rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
    assert r.reaches_on == ("subscription", "twelve months")


def test_two_quoted_wordings_for_one_position_are_asked_again(corpus, queue):
    wording = POS7_NEW.split("\n")[0]
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(f'R1 "{wording}" or "{wording}"', sent=line)
    with pytest.raises(ValueError, match="Ask the firm which they meant"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))


@pytest.mark.parametrize("reply", ['R1 "yes"', 'R1 "Keep it"'])
def test_a_short_quote_is_refused_for_what_it_is(corpus, queue, reply):
    """The refusal said "neither a plain yes or no", which a quoted yes is."""
    f = _found(corpus, "position", "POS7")
    entry, line = rulings.ask(f, POS7_NEW, queue=queue, corpus=corpus)
    rid, answer = notifying.reply_in(reply, sent=line)
    with pytest.raises(ValueError, match="too short to be a position"):
        rulings.record_ruling(corpus, rulings.settle(queue, rid, answer))
