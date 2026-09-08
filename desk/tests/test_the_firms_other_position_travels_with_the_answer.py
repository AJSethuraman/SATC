"""A ratified position applied to the WRONG FACTS serves confidently wrong.

THE INCIDENT, 7 September 2026, found by the Forge on desk 0.7.3 and the sharpest
thing any run has produced. `cash-and-bank` holds two ratified positions on one
section of IRS Pub. 583, with opposite answers:

    "— what the statement did not yet include"  ->  a reconciling item, no entry
    "— what the books are updated for"          ->  an entry in the books

Asked about a deposit made on the last day of the month and not yet on the
statement, an agent cited the second. `serve` served it: `binding=True`, in the
firm's own words. The desk's OWN recorded problem CB1 gives the answer as "a
reconciling item, no entry in the books". The engine served the opposite.

WHY NOTHING CAUGHT IT, which is the part that matters. `_check` refuses a
conclusion that CONTRADICTS a ratified position — an agent arguing with the firm.
Here the agent did not argue: it quoted the firm exactly, about a different rule.
No check in this engine is a statement about which of two adjacent rules the
facts are in, and none can be — that needs the facts, which the desk does not
have.

SO THE ALTERNATIVE IS SHOWN RATHER THAN THE ERROR CAUGHT. Same trade `passage`
made. The tester: *"The reader is shown one of two adjacent rules and not told
the other exists."* These tests hold that shut.
"""
import pytest

import ask
import engine
import record

CITE = 'IRS Pub. 583 (12/2024), "Reconciling the checking account"'
BOOKS = f"{CITE} — what the books are updated for"
STATEMENT = f"{CITE} — what the statement did not yet include"

DEPOSIT_IN_TRANSIT = ("a deposit was made on the last day of the month and has "
                      "not appeared on the bank statement")


@pytest.fixture
def cash():
    return record.load(record.Path(__file__).resolve().parent.parent
                       / "desks" / "cash-and-bank")


def _serve(question, position, citation):
    return ask.answer(question, "cash-and-bank", position=position,
                      citation=citation, keep=False)


# ---------------------------------------------------------------- the record

def test_the_desk_still_holds_two_opposite_positions_on_one_passage(cash):
    """The premise. If this desk is ever rewritten, these tests must be re-read."""
    rat = {p.citation: p.position for p in cash.positions if not p.proposed}
    assert rat[BOOKS] == "an entry in the books"
    assert rat[STATEMENT] == "a reconciling item, no entry in the books"


def test_alongside_finds_the_other_half_of_a_split_citation(cash):
    other = cash.alongside(BOOKS)
    assert [p.citation for p in other] == [STATEMENT]
    assert other[0].position == "a reconciling item, no entry in the books"


def test_it_is_symmetric(cash):
    assert [p.citation for p in cash.alongside(STATEMENT)] == [BOOKS]


def test_a_citation_is_never_its_own_sibling(cash):
    assert BOOKS not in [p.citation for p in cash.alongside(BOOKS)]


def test_the_bare_section_reaches_both_halves(cash):
    """An agent citing the section with no qualifier most needs telling."""
    assert {p.citation for p in cash.alongside(CITE)} == {BOOKS, STATEMENT}


def test_different_paragraphs_of_one_regulation_are_not_siblings():
    """The stem is the firm's hand-written note, not the regulation number.

    `capitalization-and-de-minimis` holds positions on § 1.263(a)-1(f)(5) and on
    § 1.263(a)-1(f)(1)(ii)(B). Those are different rules and a reader shown one
    beside the other learns nothing. A looser rule -- same source, or same
    regulation -- would fire here and teach the reader to skip the block.
    """
    desk = record.load(record.Path(__file__).resolve().parent.parent
                       / "desks" / "capitalization-and-de-minimis")
    for p in desk.positions:
        assert desk.alongside(p.citation) == (), p.citation


def test_it_fires_on_exactly_one_pair_in_the_whole_corpus():
    """THE DENOMINATOR. A guard that fires everywhere is one nobody reads."""
    root = record.Path(__file__).resolve().parent.parent / "desks"
    fired = [(d.name, p.citation) for d in sorted(root.iterdir()) if d.is_dir()
             for desk in [record.load(d)] for p in desk.positions
             if not p.proposed and desk.alongside(p.citation)]
    assert sorted(n for n, _ in fired) == ["cash-and-bank", "cash-and-bank"]


def test_a_proposed_position_is_never_shown_as_a_sibling(cash):
    """A suggestion nobody said yes to must not read as the firm's word."""
    import dataclasses
    proposed = dataclasses.replace(
        [p for p in cash.positions if p.citation == STATEMENT][0],
        ratified="")                       # `proposed` is "not yet ratified"
    kept = [p for p in cash.positions if p.citation != STATEMENT]
    desk = dataclasses.replace(cash, positions=tuple(kept) + (proposed,))
    assert desk.alongside(BOOKS) == ()


# ------------------------------------------------------- what leaves the desk

def test_the_wrong_answer_still_serves():
    """NOT A REGRESSION -- the honest statement of what this does not fix.

    The engine cannot tell that these facts are the other rule's. It never
    could, and this change did not give it the ability. What changed is only
    whether the reader can tell.
    """
    out = _serve(DEPOSIT_IN_TRANSIT, "an entry in the books", BOOKS)
    assert isinstance(out, engine.Served)
    assert out.binding is True


def test_the_served_answer_carries_the_position_that_contradicts_it():
    out = _serve(DEPOSIT_IN_TRANSIT, "an entry in the books", BOOKS)
    assert out.alongside == ((STATEMENT, "a reconciling item, no entry in the books"),)


def test_printing_it_shows_both_answers():
    """The whole value. Two opposite answers, side by side, on one screen."""
    shown = str(_serve(DEPOSIT_IN_TRANSIT, "an entry in the books", BOOKS))
    assert "an entry in the books" in shown
    assert "a reconciling item, no entry in the books" in shown
    assert "what the statement did not yet include" in shown


def test_it_says_the_facts_decide_and_that_nothing_looked_at_them():
    shown = str(_serve(DEPOSIT_IN_TRANSIT, "an entry in the books", BOOKS))
    assert "nothing here has looked at the facts" in shown


def test_alongside_is_empty_on_an_ordinary_answer():
    """A control. Set on every answer, it would say nothing on any."""
    out = ask.answer(
        "we bought a forklift, is the invoice price deducted or capitalized",
        "fixed-assets",
        position="capitalized as a unit of property",
        citation="26 CFR 1.263(a)-2(d)(1)", keep=False)
    assert isinstance(out, engine.Served)
    assert out.alongside == ()
    assert "THE FIRM HOLDS ANOTHER POSITION" not in str(out)


def test_the_caller_cannot_supply_it():
    """COMPUTED, NOT PASSED. An answer that can be built without it will be."""
    import inspect
    assert "alongside" not in inspect.signature(ask.answer).parameters
    assert "alongside" not in inspect.signature(engine.serve).parameters
