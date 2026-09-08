"""The judge: a second reader handed the paragraph and the conclusion.

WHAT IT IS FOR, IN ONE RUN. On 7 September 2026 a session cited
§ 1.263(a)-2(d)(1) — whose text opens *"a taxpayer must capitalize amounts paid
to acquire or produce a unit of real or personal property"* — to conclude
**"deducted, not capitalized"**. Every exact check in this engine passed, and
was right to: the citation resolves, the desk holds it, the publisher governs
the domain, no ratified position was contradicted. It was SERVED.

`test_the_seventh_september_answer_is_still_served_unjudged` pins that, so
nobody reads this file as a claim the engine got smarter. It did not. What
changed is that a second reader can now be asked, and the engine will act on
their answer — and the FIRST test below shows the same call, judged, refused.

THE ENGINE DOES NOT JUDGE. It checks the one thing about a judgment that is
checkable without reading: that the words the judge rests on are in the passage.
Everything else here is about keeping that honest — the judge is not the
answerer, a judgment cannot rescue a refusal, a quote is a quote.
"""
import pytest

import ask
import engine
import judging
from conftest import DESKS

Q = "we bought a forklift. is the invoice price deducted or capitalized?"
CIT = "26 CFR 1.263(a)-2(d)(1)"
DESK = "fixed-assets"

#: Words that really are in that paragraph, in that order, with the procedure
#: between them marked rather than transcribed.
REAL = ("a taxpayer must capitalize amounts paid to acquire or produce a unit "
        "of real or personal property [...] include the invoice price")


def _answer(**kw):
    kw.setdefault("model", "answerer")
    kw.setdefault("keep", False)
    return ask.answer(Q, DESK, citation=CIT, **kw)


# ------------------------------------------- the run this was built for

def test_the_seventh_september_answer_still_passes_every_gate_but_the_judge():
    """THE CONTROL, and it must stay red-adjacent forever: nothing added here
    made the engine able to tell that this paragraph refutes this conclusion.

    REWRITTEN 8 SEPTEMBER, AND THE FACT IT PINS IS UNCHANGED. It used to assert
    the answer was SERVED unjudged; every desk now declares `Judged: required`
    (#346), so unjudged refuses — for want of a reader, and for nothing else.
    The point was never that it was served: it was that no gate in this engine
    can see what is wrong with it, and the refusal below says so in as many
    words. A judged run of the same call is the next test, and it refuses on the
    merits.
    """
    out = _answer(position="deducted, not capitalized")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "not_judged", (
        "something OTHER than the missing judge caught it, which would mean "
        "this control has stopped being the control")
    assert "Nothing is wrong with the answer or with the record" in out.detail

    # AND IT REALLY WAS SERVED UNTIL THE JUDGE WAS REQUIRED. Read off a desk
    # that does not require one, so the claim is measured rather than
    # remembered — otherwise the paragraph above is a story about the past.
    import dataclasses
    import record
    desk = dataclasses.replace(record.load(DESKS / DESK), judged=record.OPTIONAL)
    served = engine.serve(
        engine.Answer(position="deducted, not capitalized", citation=CIT),
        desk, question=Q)
    assert isinstance(served, engine.Served)
    assert served.position == "deducted, not capitalized"


def test_and_a_second_reader_stops_it():
    said_no = judging.Judgment(
        by="second-reader", supports=False,
        because="the paragraph requires capitalization of amounts paid to "
                "acquire a unit of personal property, which is the opposite")
    out = _answer(position="deducted, not capitalized", judged=said_no)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "citation_does_not_support"
    assert "second-reader" in out.detail
    assert out.desk == DESK, "a refusal that does not name its desk is unusable"


def test_the_refusal_carries_the_reader_s_own_words():
    """Not a verdict flag. The answerer has to be able to act on it."""
    said_no = judging.Judgment(by="second-reader", supports=False,
                               because="this paragraph is about acquisition, "
                                       "and the question was about disposal")
    out = _answer(position="deducted, not capitalized", judged=said_no)
    assert "about acquisition" in out.detail
    assert out.ask, "a refusal a person can resolve and no question in it"


# ---------------------------------------- what the engine checks, and only that

def test_a_judgment_that_quotes_the_passage_is_served():
    out = _answer(position="capitalized",
                  judged=judging.Judgment(by="second-reader", supports=True,
                                          because=REAL))
    assert isinstance(out, engine.Served)
    assert out.judged.stands
    assert out.judged.by == "second-reader"


def test_a_judgment_that_quotes_what_is_not_there_is_refused_as_a_judgment():
    """AND NOT AS A BAD ANSWER, which is the whole distinction. Nobody has read
    the answer; the reading failed. Filing this as `citation_does_not_support`
    would put a defect in the second reader into the queue that reads out what
    the RECORD is missing."""
    out = _answer(position="capitalized",
                  judged=judging.Judgment(
                      by="second-reader", supports=True,
                      because="forklifts are always capitalized under this rule"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "judgment_not_in_the_passage"
    assert out.reason in engine.REASONS
    assert "not refused on its merits" in out.detail


def test_the_refusal_names_the_words_that_were_not_there():
    out = _answer(position="capitalized",
                  judged=judging.Judgment(by="second-reader", supports=True,
                                          because="forklifts are always capitalized"))
    assert "forklifts are always capitalized" in out.detail


def test_an_omission_may_be_marked_and_is_matched_in_order():
    """The same mark, the same meaning, the same code as a stored passage's —
    `comparing`, one folding table. A judge pointing at two clauses of a long
    paragraph should not have to transcribe the procedure between them."""
    out = _answer(position="capitalized",
                  judged=judging.Judgment(by="second-reader", supports=True,
                                          because=REAL))
    assert isinstance(out, engine.Served)


def test_but_a_mark_may_not_reorder_the_paragraph():
    """Strictness is the point of `elided_match`: each segment is found after
    the last one ended. Otherwise a judge could assemble a sentence the
    regulation does not contain out of words it does."""
    backwards = ("include the invoice price [...] a taxpayer must capitalize "
                 "amounts paid to acquire")
    out = _answer(position="capitalized",
                  judged=judging.Judgment(by="second-reader", supports=True,
                                          because=backwards))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "judgment_not_in_the_passage"


def test_curly_quotes_and_odd_spacing_do_not_defeat_it():
    """A judge pasting from a browser gets smart quotes. That is not a defect
    in the reading and must not be reported as one."""
    out = _answer(position="capitalized",
                  judged=judging.Judgment(
                      by="second-reader", supports=True,
                      because="a  taxpayer   must\ncapitalize amounts paid"))
    assert isinstance(out, engine.Served)


# -------------------------------------------------- who is allowed to judge

def test_the_answerer_may_not_judge_its_own_answer():
    """C6 — the preparer does not become the verifier. It RAISES rather than
    refusing: a caller handing the engine one model wearing both hats has broken
    the contract, and filing that in `unsupported/` would record it as a finding
    about the record when it is a finding about the caller."""
    with pytest.raises(judging.JudgingError, match="both answered and judged"):
        _answer(position="capitalized",
                judged=judging.Judgment(by="answerer", supports=True,
                                        because=REAL))


def test_a_judgment_with_no_author_is_not_a_judgment():
    with pytest.raises(judging.JudgingError, match="no author"):
        judging.Judgment(by="  ", supports=True, because=REAL)


def test_a_yes_with_no_words_in_it_is_not_a_judgment():
    with pytest.raises(judging.JudgingError, match="quote what"):
        judging.Judgment(by="second-reader", supports=True, because="")


def test_and_neither_is_a_bare_no():
    with pytest.raises(judging.JudgingError, match="bare no"):
        judging.Judgment(by="second-reader", supports=False, because="")


def test_an_unnamed_answerer_does_not_disable_the_check():
    """`model` is optional on `ask.answer`, and an empty one must not be read as
    'the judge is somebody else'. It cannot be compared, so it is not — but the
    judgment is still checked against the passage."""
    out = _answer(position="capitalized", model="",
                  judged=judging.Judgment(by="second-reader", supports=True,
                                          because="not in this paragraph at all"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "judgment_not_in_the_passage"


# ------------------------------------- it may add a refusal, never remove one

def test_a_judgment_cannot_rescue_an_answer_the_gate_refused():
    """Every stage after the gate has this property and it is the reason they
    run in the order they do. A second reader saying 'this is fine' about an
    answer with no authority behind it is a second reader who was not asked."""
    out = ask.answer(Q, DESK, position="capitalized",
                     citation="26 CFR 1.999-9(z)", keep=False, model="answerer",
                     judged=judging.Judgment(by="second-reader", supports=True,
                                             because="anything at all"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_absent", "the judge changed the refusal"


def test_every_desk_now_requires_one_and_says_so_in_its_own_file():
    """The firm decided it on the docket, 8 September 2026, asked which desks
    may not serve unjudged: *"The judge can look at it all I guess?"*

    DECLARED IN THE RECORD RATHER THAN IN THE CODE, and the hedge in that answer
    is why. Lifting it from any desk is one line of that desk's SUBJECTS.md; a
    requirement in `ask.py` would need a session. This reads the seven files
    rather than a constant, so a desk that quietly stops declaring it goes red.
    """
    import record
    for d in sorted(p for p in DESKS.iterdir() if p.is_dir()):
        desk = record.load(d)
        assert desk.needs_a_judge, f"{desk.name} serves what nobody read"


def test_an_unjudged_answer_refuses_and_says_how_to_supply_one():
    """A CALLER CONTRACT, NOT A FINDING ABOUT THE RECORD. Nothing is missing
    from the desk; whoever wired the caller has to arrange a second reader."""
    out = _answer(position="capitalized")
    assert isinstance(out, engine.Refusal)
    assert out.reason == "not_judged"
    assert "judging.Judgment" in out.ask, "it must say how to supply one"
    assert "OTHER than the one that answered" in out.ask
    assert out.desk == DESK


def test_the_unjudged_refusal_is_not_filed_in_the_record_s_queue(tmp_path):
    """`unsupported/` is what says the RECORD is missing something. A missing
    judgment is the caller's half, so filing it would put a work item in a queue
    nobody can act on and inflate the one count that is meant to mean something.
    """
    import shutil
    desks = tmp_path / "desks"
    desks.mkdir()
    shutil.copytree(DESKS / DESK, desks / DESK)
    queue = desks / DESK / "unsupported" / "asked.md"
    before = queue.read_text(encoding="utf-8") if queue.exists() else ""

    out = ask.answer(Q, DESK, position="capitalized", citation=CIT,
                     desks=desks, keep=True)
    assert isinstance(out, engine.Refusal) and out.reason == "not_judged"
    after = queue.read_text(encoding="utf-8") if queue.exists() else ""
    assert after == before, "an unjudged answer was filed as a record gap"

    # POSITIVE PRECONDITION: `keep=True` really does file other refusals here,
    # so the assertion above is the exclusion working rather than the queue
    # being unreachable from this fixture.
    ask.answer(Q, DESK, position="capitalized",
               citation="26 CFR 1.9999-1(z)", desks=desks, keep=True)
    assert queue.exists() and queue.read_text(encoding="utf-8") != before


# ------------------------------------------------- the offline guard holds

def test_judging_cannot_reach_the_network_even_by_importing():
    """`comparing`'s docstring records what happened the one time a module on
    the front door's path could reach a fetcher by import: `proving` pulled in
    `tools/tieout.py`, which pulled in `ssl`, and every test failed inside
    `ssl.py` because this suite replaces the socket layer. `judging` imports
    `comparing` and `dataclasses` and that is the whole list.

    IT READS THE IMPORT LINES AND NOT THE PROSE. The first version scanned the
    whole file for the word `fetch` and went red on this module's own docstring
    explaining why it does not fetch -- a guard that forbids the record from
    naming the defect it exists for, which is the second time that has been
    written here in three days."""
    import ast
    import pathlib

    tree = ast.parse(pathlib.Path(judging.__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported == {"__future__", "dataclasses", "comparing"}, imported


# ------------------------------ what a judge does NOT make impossible

LEASE = ("we signed a 36-month lease on a piece of equipment. does the "
         "equipment go on our books as an asset?")

#: Words genuinely in § 1.263(a)-2(d)(1), in order. Nothing invented.
GENUINE = ("a taxpayer must capitalize amounts paid to acquire or produce a "
           "unit of real or personal property")


def test_a_careless_judge_quoting_real_words_still_serves_a_wrong_answer():
    """THE LIMIT, MEASURED ON THE FORGE AND PINNED HERE SO NOBODY OVERSELLS IT.

    The desk ran seven trials against 0.11.0 and reported the one that matters:
    the SAME quotation supports both verdicts. A careless second reader quotes
    *"a taxpayer must capitalize amounts paid to acquire or produce a unit of
    real or personal property"* — really there, really in order — says yes, and
    the lease answer is served. A careful one quotes the identical words, says
    no, and it is refused.

        "the judge does not make a wrong answer impossible — it makes a wrong
         answer ATTRIBUTABLE. Instead of 'nobody checked', the record now says
         WHO checked, WHAT they quoted, and that they said yes. A reviewer can
         disagree with a named reader holding a specific quotation. Nobody can
         disagree with 'unchecked'."

    That is the gain and it is a real one. It is NOT a gate in the sense the
    domain check is a gate: the domain check can be right without a human; this
    one is exactly as good as the second reader, and two models sharing a blind
    spot will agree.

    So this test exists to go red if anyone ever writes that the judge stops
    wrong answers. It does not."""
    out = ask.answer(LEASE, DESK, position="yes - capitalize the equipment as a "
                                           "unit of property",
                     citation=CIT, keep=False, model="answerer",
                     judged=judging.Judgment(by="careless-reader", supports=True,
                                             because=GENUINE))
    assert isinstance(out, engine.Served), "the judge became a gate; read the docstring"
    assert out.judged.stands


def test_and_the_identical_quotation_refuses_when_the_reader_is_careful():
    """The other half of the same pair. The engine did not change; the reader did."""
    out = ask.answer(LEASE, DESK, position="yes - capitalize the equipment as a "
                                           "unit of property",
                     citation=CIT, keep=False, model="answerer",
                     judged=judging.Judgment(
                         by="careful-reader", supports=False,
                         because="this governs amounts paid to ACQUIRE property, "
                                 "and a lessee under a true lease has not "
                                 "acquired it"))
    assert isinstance(out, engine.Refusal)
    assert out.reason == "citation_does_not_support"


def test_the_record_says_who_read_it_which_is_the_whole_gain():
    """`unchecked` says nobody looked. This says who looked and what they held."""
    out = ask.answer(LEASE, DESK, position="yes - capitalize the equipment as a "
                                           "unit of property",
                     citation=CIT, keep=False, model="answerer",
                     judged=judging.Judgment(by="careless-reader", supports=True,
                                             because=GENUINE))
    assert out.judged.by == "careless-reader"
    assert out.judged.because == GENUINE
