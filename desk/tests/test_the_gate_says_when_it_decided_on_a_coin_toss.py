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

import ask
import domains
import engine
import record

NATURAL = ("we signed a 36-month lease on a piece of equipment. does the "
           "equipment go on our books as an asset?")
KEYWORDS = "is the leased equipment booked as an asset?"
FORKLIFT = "we bought a forklift. is the invoice price deducted or capitalized?"
CIT = "26 CFR 1.263(a)-2(d)(1)"


def _served(question):
    return ask.answer(question, "fixed-assets",
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

def test_the_answer_says_the_gate_did_not_decide_it():
    out = _served(NATURAL)
    assert isinstance(out, engine.Served), "the gate refused; the trap is closed elsewhere"
    assert out.straddle
    assert "did not decide" in out.straddle.lower()
    assert "name sort" in out.straddle


def test_it_names_the_body_that_does_govern_the_other_half():
    out = _served(NATURAL)
    assert "Financial Accounting Standards Board" in out.straddle
    assert "us-gaap" in out.straddle


def test_and_says_no_desk_here_holds_it():
    out = _served(NATURAL)
    assert "NO DESK HERE HOLDS IT" in out.straddle


def test_that_last_part_is_read_off_the_record_and_not_asserted():
    """A sentence claiming the record holds nothing is a claim that goes stale
    the day the firm admits a publisher. So it asks the desk's own sources."""
    desk = record.load(ask.DESKS / "fixed-assets")
    fasb = record.Source(id="SX", title="FASB ASC", tier="primary",
                         access="public_fetch", may_store=False,
                         checked="2026-09-08", citation_prefix="ASC",
                         url="https://asc.fasb.org/", note="")
    widened = dataclasses.replace(desk, sources=tuple(desk.sources) + (fasb,))
    note = engine._straddle_note(domains.classify(NATURAL), widened)
    assert "NO DESK HERE HOLDS IT" not in note
    assert "does hold us-gaap" in note


def test_the_note_stays_short():
    """It will appear most often on answers that were already right — four of
    the five straddles on the record are correct tax answers. A warning long
    enough to skip is one that gets skipped."""
    out = _served(NATURAL)
    assert len(out.straddle.split()) <= 70, out.straddle


def test_it_is_printed_above_the_authority_so_it_cannot_be_read_past():
    text = str(_served(NATURAL))
    assert text.index("THE GATE DID NOT DECIDE") < text.index("THE AUTHORITY, in full")


#: A question that straddles and is NOT a tie, AND is served: `federal-tax`
#: 3-1 over `us-gaap`, cited to a Treasury regulation irs.gov governs. It exists
#: because the obvious control -- the keyword phrasing -- is REFUSED on the body
#: of authority, so `straddle` is empty on it whatever the note does, and a
#: mutation firing the note on every straddle passed all sixteen tests without
#: it. Fourth self-proving control caught by mutation this week.
DECIDED = ("the client leased a truck and also bought shop supplies; is the "
           "invoice price deducted or capitalized under the de minimis safe "
           "harbor?")


def test_a_served_straddle_decided_on_the_words_carries_nothing():
    v = domains.classify(DECIDED)
    assert v.straddles and not v.tied, "this control no longer straddles"
    out = ask.answer(DECIDED, "fixed-assets", position="capitalized",
                     citation=CIT, keep=False, model="answerer")
    assert isinstance(out, engine.Served), out
    assert out.straddle == "", (
        "the note fired on a straddle the words decided; it is for coin "
        "tosses, and firing it everywhere is how it becomes boilerplate")


def test_the_keyword_phrasing_carries_no_such_note():
    """It was decided on the words. Warning there would be the boilerplate this
    is trying not to become."""
    out = ask.answer(KEYWORDS, "fixed-assets", position="capitalized",
                     citation=CIT, keep=False, model="answerer")
    # us-gaap governs, so irs.gov does not, so this refuses on the body of
    # authority — which is the gate working. Either way there is no coin toss.
    assert getattr(out, "straddle", "") == ""


def test_an_answer_the_gate_decided_on_evidence_carries_nothing():
    out = ask.answer(FORKLIFT, "fixed-assets", position="capitalized",
                     citation=CIT, keep=False, model="answerer")
    assert isinstance(out, engine.Served)
    assert out.straddle == ""


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
