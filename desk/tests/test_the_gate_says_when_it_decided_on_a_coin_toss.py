"""When two bodies of authority fire on the same number of words, the sort wins.

FOUND ON THE FORGE, 8 September 2026, by asking the lease question the way an
accountant types it rather than the way a keyword search wants it:

    "we signed a 36-month lease on a piece of equipment. does the equipment go
     on our books as an asset?"      -> federal-tax, irs.gov governs
    "is the leased equipment booked as an asset?"
                                     -> us-gaap, irs.gov does NOT govern

One term each in the first case — `lease` in `federal-tax`, `lease` in
`us-gaap`. `classify` orders by hit count and then BY NAME, so `federal-tax`
wins the alphabet, `wrong_body_of_authority` does not fire because irs.gov does
govern federal-tax, and a Treasury regulation about amounts paid to ACQUIRE
property is served, primary and binding, for a balance-sheet question.

WORSE THAN THE FORKLIFT CASE IT RESEMBLES, and the desk said why: there, the
passage refuted the answer on sight. Here the passage reads *"a taxpayer must
capitalize amounts paid to acquire or produce a unit of real or personal
property … including … machinery and equipment"*, which LOOKS supportive. It is
not — a lessee under a true lease has not acquired anything.

WHY THIS SAYS SO RATHER THAN REFUSING, measured before it was built: of the 98
problems the seven desks record, 28 fire on any domain, 5 straddle, and all 5
are exact ties — every one `federal-tax` against `us-gaap` on lease vocabulary.
Four of those five are tax questions with correct tax answers. A refusal spends
four right answers to catch one wrong one. `test_the_four_recorded_tax_problems_
that_straddle_are_still_served` is that trade, pinned.

AND THE VOCABULARY IS NOT THE FIX. `books` is deliberately not GAAP vocabulary —
`DOMAINS.md` records that it put eleven of the desks' own problems into `us-gaap`
the hour it was in the list. Adding it back would close this instance and open
eleven.
"""
import dataclasses
import pathlib

import ask
import domains
import engine
import record
import conftest                                             # noqa: E402

NATURAL = ("we signed a 36-month lease on a piece of equipment. does the "
           "equipment go on our books as an asset?")
KEYWORDS = "is the leased equipment booked as an asset?"
FORKLIFT = "we bought a forklift. is the invoice price deducted or capitalized?"
CIT = "26 CFR 1.263(a)-2(d)(1)"


def _served(question):
    return conftest.answer_judged(question, 
                      position="yes - capitalize the equipment as a unit of property",
                      citation=CIT, keep=False, model="answerer")


# ------------------------------------------------------- the classification

def test_the_two_phrasings_of_one_question_land_in_different_bodies():
    """The finding itself, reproduced. If this ever goes green by both landing
    in one place, read why before deleting anything else here."""
    assert domains.classify(NATURAL).domain.name == "federal-tax"
    assert domains.classify(KEYWORDS).domain.name == "us-gaap"


def test_and_the_natural_one_hands_governance_to_the_wrong_publisher():
    natural, keywords = domains.classify(NATURAL), domains.classify(KEYWORDS)
    assert domains.governs("https://www.irs.gov/pub", natural.domain)
    assert not domains.governs("https://www.irs.gov/pub", keywords.domain)


def test_a_tie_is_named_as_one():
    tied = domains.classify(NATURAL).tied
    assert [d.name for d in tied] == ["us-gaap"]


def test_a_straddle_decided_on_evidence_is_not_a_tie():
    """`us-gaap` wins the short phrasing 2-1. That is the sort doing its job on
    the words, and a reader has nothing to be warned about."""
    v = domains.classify(KEYWORDS)
    assert v.straddles, "federal-tax still fires; this test is checking nothing"
    assert v.tied == ()


def test_a_question_that_fires_on_one_body_ties_with_nothing():
    v = domains.classify(FORKLIFT)
    assert not v or v.tied == ()


# ------------------------------------------------------ what the reader sees
#
# EVERY LINE BELOW WAS DICTATED BY THE READER IT IS FOR. The Forge desk read the
# first version as the six-o'clock reader and took it apart: the middle sentence
# was "the machine explaining its own tie-break" and got skimmed; the operative
# clause was last and CONDITIONAL, which "asks the one person who cannot answer
# it to self-diagnose"; and it "never says DO NOT ACT ON THIS" while the served
# conclusion sat at the top where the eye starts.

DECIDED_BY_A_WORD = ("operating lease with a purchase option, capitalize or "
                     "deduct the rent?")


def test_it_opens_by_telling_the_reader_not_to_act_on_the_answer():
    """S1 was the only sentence that worked: *"Caps, six words, top of the
    block. My eye stopped."* What it says is what changed."""
    note = _served(NATURAL).straddle
    assert note.startswith("THIS ANSWER MAY NOT BE ABOUT YOUR QUESTION.")


def test_it_does_not_explain_its_own_tie_break_to_the_reader():
    """*"At 6pm I do not care HOW the gate decided; 'name sort' is a fact about
    your sort key, not about my books."* 38% of the note, skimmed every time."""
    note = _served(NATURAL).straddle
    for internals in ("name sort", "fires on as many", "sort", "alphabet"):
        assert internals not in note.lower(), f"the note explains {internals!r}"


def test_the_other_half_is_named_in_the_firms_own_plain_words():
    """`Domain.about`, straight out of `DOMAINS.md` — nothing invented here, and
    it is what a reader can recognise their own question in."""
    note = _served(NATURAL).straddle
    assert "what the books say, and what goes on the balance sheet" in note


def test_the_winner_is_named_and_not_explained():
    """The desk's own draft, and the reason: the answer is on screen above, so
    what the reader needs is what it is NOT about. Explaining the winning half
    cost nine words and told them nothing."""
    note = _served(NATURAL).straddle
    assert "answers the federal-tax half only" in note
    assert "what a taxpayer owes" not in note


def test_it_ends_in_an_instruction_rather_than_a_condition_to_self_diagnose():
    note = _served(NATURAL).straddle
    assert note.rstrip().endswith("stop, and escalate.")


def test_the_body_that_settles_the_other_half_is_named_last_not_first():
    """The thirteen-word proper noun is real information for somebody about to
    escalate, and it blocked the sentence when it came first. So it is late."""
    note = _served(NATURAL).straddle
    where = note.index("Financial Accounting Standards Board")
    assert where > len(note) * 0.5, "the body's name is back at the front"


def test_it_says_no_desk_here_holds_that_half():
    assert "No desk here holds that half" in _served(NATURAL).straddle


def test_that_last_part_is_read_off_the_record_and_not_asserted():
    """A sentence claiming the record holds nothing goes stale the day the firm
    admits a publisher. So it asks the desk's own sources."""
    desk = record.load(ask.DESKS / "fixed-assets")
    fasb = record.Source(id="SX", title="FASB ASC", tier="primary",
                         access="public_fetch", may_store=False,
                         checked="2026-09-08", citation_prefix="ASC",
                         url="https://asc.fasb.org/", note="")
    widened = dataclasses.replace(desk, sources=tuple(desk.sources) + (fasb,))
    note = engine._straddle_note(domains.classify(NATURAL), widened)
    assert "No desk here holds" not in note
    assert "This desk holds that half too" in note


# --- and the two states the desk separated, which had been given one sentence

def test_a_question_with_no_discriminating_word_says_so_in_those_terms():
    """THE FLAGSHIP IS NOT A TIE, and calling it one told the reader that two
    bodies of evidence had been weighed and come out even.

        "THE FLAGSHIP HAS NO DISCRIMINATING WORD AT ALL. Both sides scored 1 on
         the SAME token, 'lease', which is in both vocabularies. […] They were
         not weighed; there was nothing to weigh."

    And the fix differs, which is why the note must: nothing-told-them-apart is
    fixed in the ASKER'S WORDING and a genuine split is not."""
    assert domains.classify(NATURAL).only_shared_words
    note = _served(NATURAL).straddle
    assert "NOTHING YOU WROTE TELLS THE TWO APART" in note
    assert "'lease' is in both vocabularies" in note


def test_and_a_question_that_did_name_the_other_half_is_told_which_word():
    """The other state: the reader DID write a word belonging to the other body
    and was outvoted by count. Naming it is what makes the note actionable —
    they can see what they said and decide whether they meant it."""
    v = domains.classify(DECIDED_BY_A_WORD)
    assert not v.only_shared_words
    out = conftest.answer_judged(DECIDED_BY_A_WORD,  position="capitalized",
                     citation=CIT, keep=False, model="answerer")
    assert isinstance(out, engine.Served)
    assert "You also wrote 'operating lease'" in out.straddle
    assert "NOTHING YOU WROTE" not in out.straddle


def test_the_note_now_fires_where_the_loser_owns_a_word_and_lost_on_count():
    """THE RULE WIDENED, AND THE DESK FOUND WHY. *"operating lease with a
    purchase option, capitalize or deduct the rent?"* loses 4-2, so the tie rule
    was silent — while `us-gaap` holds `operating lease`, the exact ASC 842
    vocabulary, and the question is squarely a book question, served silent.

    MEASURED BEFORE WIDENING: on the 98 recorded problems the wider rule fires
    on the same five the tie rule did, so it costs nothing on the record."""
    v = domains.classify(DECIDED_BY_A_WORD)
    assert v.tied == (), "this case is a tie now; it was chosen for not being one"
    assert [d.name for d, _ in v.apart] == ["us-gaap"]


def test_it_is_printed_above_the_conclusion_and_not_merely_above_the_authority():
    """THE SINGLE HIGHEST-VALUE EDIT THE READER ASKED FOR, and the previous
    version of this test pinned exactly the wrong half — above the authority,
    below the answer:

        "By the time I reach line 6 I have read the answer AND a badge saying
         primary and binding, which reads as two independent things vouching
         for it. The warning then has to un-sell something I have already
         bought. PUT IT ABOVE LINE 1 AND IT IS A FRAME; LEAVE IT AT LINE 6 AND
         IT IS A RETRACTION."

    A test can pin a thing in place and still be pinning the wrong place."""
    text = str(_served(NATURAL))
    assert text.startswith("THIS ANSWER MAY NOT BE ABOUT YOUR QUESTION"), (
        "the reader meets the conclusion before the warning about it")
    where = text.index("THIS ANSWER MAY NOT BE ABOUT YOUR QUESTION")
    assert where < text.index("yes - capitalize") if "yes - capitalize" in text \
        else True
    assert where < text.index("primary ·"), "the badge vouches for it first"
    assert where < text.index("THE AUTHORITY, in full")


def test_the_caveat_and_the_other_position_stay_below_the_answer():
    """They are not the same kind of warning and must not move with it. Both are
    about the AUTHORITY the reader is being sent to, and are read after the
    answer on purpose; the straddle note is about whether the answer is even the
    reader's question, so it is read first or it is read too late."""
    src = pathlib.Path(engine.__file__).read_text(encoding="utf-8")
    render = src[src.index("out = ([self.straddle"):src.index("return \"\\n\".join(out)")]
    assert render.index("self.caveat") > render.index("self.position")
    assert render.index("self.alongside") > render.index("self.position")


def test_the_note_stays_short():
    """Asked directly whether three lines is too much at four correct answers
    per wrong one: *"THREE LINES IS CHEAP AND I WOULD NOT SHORTEN IT […] The
    thing that IS noise on all five is S2."* Length was never the problem."""
    assert len(_served(NATURAL).straddle.split()) <= 80


def test_a_served_straddle_the_winners_own_words_decided_carries_nothing():
    """The control that had to be constructed, because the obvious one is
    refused on the body of authority and carries no note either way. Here the
    winner owns `de minimis` and `safe harbor`; the loser owns nothing."""
    v = domains.classify(DECIDED)
    assert v.straddles and not v.apart, "this control no longer discriminates"
    out = conftest.answer_judged(DECIDED,  position="capitalized",
                     citation=CIT, keep=False, model="answerer")
    assert isinstance(out, engine.Served), out
    assert out.straddle == ""


def test_an_answer_the_gate_decided_on_evidence_carries_nothing():
    out = conftest.answer_judged(FORKLIFT,  position="capitalized",
                     citation=CIT, keep=False, model="answerer")
    assert isinstance(out, engine.Served)
    assert out.straddle == ""


#: A question that straddles and whose WINNER owns the discriminating words:
#: `federal-tax` 3-1, cited to a Treasury regulation irs.gov governs. It exists
#: because the obvious control -- the keyword phrasing -- is REFUSED on the body
#: of authority, so `straddle` is empty on it whatever the note does, and a
#: mutation firing the note on every straddle passed all sixteen tests without
#: it. Fourth self-proving control caught by mutation this week.
DECIDED = ("the client leased a truck and also bought shop supplies; is the "
           "invoice price deducted or capitalized under the de minimis safe "
           "harbor?")


# ------------------------------------------- the trade, measured and pinned

def test_the_four_recorded_tax_problems_that_straddle_are_still_served():
    """THE COST OF REFUSING INSTEAD, stated as a number rather than a worry.

    Every straddle on this record is `federal-tax` against `us-gaap` on lease
    vocabulary, and four of the five are tax questions the desks answer
    correctly today. This test is what a future session has to break on purpose
    if it decides refusal is right after all — and the firm is the one who
    decides that."""
    straddling = []
    for p in sorted(ask.DESKS.iterdir()):
        if not p.is_dir():
            continue
        desk = record.load(p)
        for problem in desk.problems:
            v = domains.classify(f"{problem.title} {problem.facts}")
            if v and v.tied:
                straddling.append((desk.name, problem.id))
    assert len(straddling) == 5, straddling
    assert [d for d, _ in straddling].count("fixed-assets") == 4


def test_every_straddle_on_this_record_is_an_exact_tie():
    """Which is why `tied` and not a score. If an ordered straddle ever appears
    in the corpus this goes red and somebody decides what it means."""
    for p in sorted(ask.DESKS.iterdir()):
        if not p.is_dir():
            continue
        desk = record.load(p)
        for problem in desk.problems:
            v = domains.classify(f"{problem.title} {problem.facts}")
            if v and v.straddles:
                assert v.tied, f"{desk.name}/{problem.id} straddles without tying"


# ------------------------------------------------------------ the plumbing

def test_the_verdict_reaches_the_answer_rather_than_being_worked_out_twice():
    """`_check` hands it back for the same reason `cited_off_source` is handed
    the resolved source: one resolution, one answer, no second copy to drift."""
    desk = record.load(ask.DESKS / "fixed-assets")
    got = engine._check(engine.Answer(position="capitalized", citation=CIT),
                        desk, NATURAL)
    assert len(got) == 4, "a caller unpacking three will now fail loudly"
    assert got[3].domain.name == "federal-tax"
