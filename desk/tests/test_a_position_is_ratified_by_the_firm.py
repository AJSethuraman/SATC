"""Nothing becomes the firm's word without the firm saying so.

THE RULE IS THE OLDEST ONE HERE AND NOTHING ENFORCED IT. `positions.py`: *"An
agent only ever PROPOSES here, and the pull request is the firm's yes."* Bassy's
standing behaviour: never record a conviction without the firm's explicit yes.
Both written down, both obeyed so far, neither checked.

MEASURED, 6 SEPTEMBER 2026. A mutation appended `**Ratified:** nobody — this line
is a mutation.` to a live proposal. The whole suite — 409 tests — stayed green,
and the position went from something the engine refuses to serve to something it
serves verbatim as the firm's answer. That is the single largest thing an agent
can do to this record, and it was invisible.

WHY A ROSTER AND NOT A CLEVERER CHECK. No test can know whether a person said
yes; that fact lives outside the repository. What a test CAN do is make the
population explicit, so ratifying anything goes red on the commit that does it
and the author has to come here and write down who said it and when. The roster
is the same device as `KNOWN` in `test_corpus_is_rules.py` and `SECOND_DOCKET` in
`test_docket_form.py`, and for the same reason: a number that may only move
deliberately.

IT IS NOT A PERMISSION SYSTEM AND DOES NOT PRETEND TO BE. An agent editing this
file alongside the position defeats it in one move. What it stops is the SILENT
case — the ratification that rides along inside a large diff and that nobody,
reviewing, is given any reason to look at. That is how this would actually
happen, and it is exactly the argument `positions.py` already makes for keeping
`positions/` out of `extracted/`.
"""
from __future__ import annotations

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import record                                               # noqa: E402
from conftest import CORPUS                                  # noqa: E402

#: Every position the firm has ratified, and the day they did it. Adding a line
#: here is the act of recording a decision, so it belongs in the same commit as
#: the `Ratified:` field it describes and in no other.
#:
#: KEYED BY CITATION SINCE 10 SEPTEMBER 2026, AND THAT IS THE POINT OF THE
#: CHANGE. It was `(desk name, position id)`. `dec-kill` merged the seven
#: records, which renumbered every id — `rewards/POS3` is `POS15` — and left no
#: desk to name. A roster keyed on either would have gone red on a migration
#: rather than on a ratification, which is the opposite of what it is for. The
#: CITATION is what the firm actually said yes to and it did not move; the id
#: and the desk it came from are carried beside it as history.
#:
#: The mapping below was derived by matching each corpus position to a
#: pre-merge one on EXACT position text and citation. All twenty matched
#: uniquely; none was renamed by hand.
RATIFIED = {
    # citation: (position id, when, where it was ratified)
    "26 CFR 1.263(a)-1(f)(5)":
        ("POS1", "7 September 2026", "capitalization-and-de-minimis/POS1"),
    'IRS Tangible Property Final Regulations, "What is the de minimis safe harbor election?"':
        ("POS2", "7 September 2026", "capitalization-and-de-minimis/POS2"),
    "26 CFR 1.263(a)-1(f)(1)(ii)(B)":
        ("POS3", "5 September 2026", "capitalization-and-de-minimis/POS3"),
    'IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the statement did not yet include':
        ("POS4", "5 September 2026", "cash-and-bank/POS1"),
    'IRS Pub. 583 (12/2024), "Reconciling the checking account" — what the books are updated for':
        ("POS5", "5 September 2026", "cash-and-bank/POS2"),
    "26 CFR 1.274-12(c)(1)":
        ("POS6", "5 September 2026", "meals-and-entertainment/POS1"),
    # Ratified on the second docket and REWORDED on the fourth, 6 September
    # 2026, on the firm's instruction ("Reword POS2"). The reword is recorded on
    # the position itself; the ratification date is the day they first said yes.
    "26 CFR 1.274-11(b)(1)(i)":
        ("POS7", "5 September 2026", "meals-and-entertainment/POS2"),
    "26 CFR 1.274-12(a)(1)":
        ("POS8", "5 September 2026", "meals-and-entertainment/POS3"),
    "26 CFR 1.162-2(a)":
        ("POS9", "5 September 2026", "meals-and-entertainment/POS4"),
    # THE FIFTH DOCKET'S ONLY RATIFICATION, answered 2026-09-07T01:38Z. The firm
    # pressed "Ratify it" with no note, on a position the docket recommended
    # ratifying. It sat unbuilt for two hours because this session did not read
    # the form back — see `docs/DECISIONS-2026-09-07.md`.
    "26 CFR 1.262-1(b)(8) — the test for a serviceman's equipment":
        ("POS10", "7 September 2026", "personal-or-business/POS1"),
    # UNPINNED 10 SEPTEMBER 2026 (`dec-pos2`, "Firm policy, no citation"). Its
    # key here was `26 CFR 1.262-1(a) — the general rule` and that paragraph is
    # about costs which are PERSONAL, while the position is about costs whose
    # nature is UNKNOWN. Two independent judges refused it, correctly. THE
    # RATIFICATION DID NOT MOVE and neither did a word of the position: the firm
    # said this on 5 September and it stands. What moved is the claim about what
    # it rests on.
    "SATC policy — unidentified purchases are flagged, not drawn":
        ("POS11", "5 September 2026", "personal-or-business/POS2"),
    'IRS Pub. 587 (2025), "Actual Expenses" — utilities and services':
        ("POS12", "5 September 2026", "personal-or-business/POS3"),
    # THE FOURTH DOCKET'S ONLY RATIFICATION, and this roster is what surfaced it
    # as a decision rather than a diff. Answered "Ratify it", unamended, with no
    # note — against a recommendation to narrow it, which the firm declined.
    "PLR 201027015, LAW AND ANALYSIS":
        ("POS13", "6 September 2026", "rewards-and-information-returns/POS1"),
    "26 CFR 1.6041-1(a)(1)(iv)":
        ("POS14", "5 September 2026", "rewards-and-information-returns/POS2"),
    # THE SIXTH DOCKET'S THREE, answered 2026-09-07 13:09-13:10Z. The two
    # capitalization positions (POS1, POS2 above) had been held twice for a
    # reason the firm then removed themselves — they added the field the
    # follow-up needed. This one was ratified with its wording still owed a
    # redraft (matter `dec-register`), which is a change to how it READS and not
    # to what it says. It is also the position the 7 September reachability
    # defect was about — see
    # `test_a_ratified_position_can_actually_be_served.py`.
    "26 CFR 1.6050W-1(c)(3)":
        ("POS15", "7 September 2026", "rewards-and-information-returns/POS3"),
    'IRS Pub. 463 (2025), "Actual Car Expenses"':
        ("POS16", "5 September 2026", "vehicle-expense/POS1"),
    "26 CFR 1.280F-6(d)(2)(i)":
        ("POS17", "5 September 2026", "vehicle-expense/POS2"),
    'IRS Pub. 463 (2025), "What Are Adequate Records?"':
        ("POS18", "5 September 2026", "vehicle-expense/POS3"),
    "26 CFR 1.280F-6(e)(2)":
        ("POS19", "5 September 2026", "vehicle-expense/POS4"),
    "26 CFR 1.62-2(c)(1)":
        ("POS20", "5 September 2026", "vehicle-expense/POS5"),
}


def _positions():
    for q in record.load(CORPUS).positions:
        yield q


def test_nothing_is_ratified_that_is_not_on_the_roster():
    live = {q.citation for q in _positions() if not q.proposed}
    new = live - set(RATIFIED)
    assert not new, (
        f"{sorted(new)} is served as the firm's own word and is not on the "
        f"roster. A position the firm never ratified, served verbatim, is the "
        f"worst thing this record can hold. If they did say yes, add it here "
        f"with the date they said it — in this commit, not a later one."
    )


def test_the_roster_does_not_outlive_what_it_describes():
    live = {q.citation for q in _positions() if not q.proposed}
    stale = set(RATIFIED) - live
    assert not stale, (
        f"{sorted(stale)} is on the roster and is not ratified in the record. "
        f"Either a ratification was withdrawn — delete the line — or a position "
        f"was renamed, and the firm's yes no longer points at anything."
    )


def test_every_ratification_says_who_and_when():
    """A `Ratified:` line that names no date is a claim about the present that
    nobody can check. The roster's date must appear in it, so the two cannot
    drift apart and quietly disagree about which decision this was."""
    for q in _positions():
        if q.proposed:
            continue
        pid, when, came_from = RATIFIED[q.citation]
        assert q.id == pid, (
            f"{q.citation} is rostered as {pid} and the record calls it "
            f"{q.id}. The roster's id is history, not a key — correct it here "
            f"rather than renaming the position.")
        assert when in q.ratified, (
            f"{q.id} ({came_from}) is rostered as ratified on {when}; its own "
            f"Ratified line says {q.ratified[:80]!r}")
        assert re.search(r"\bfirm\b", q.ratified, re.I), (
            f"{q.id} ({came_from}) does not say the firm ratified it: "
            f"{q.ratified[:80]!r}")


def test_a_proposal_is_never_served():
    """The consequence, stated where it can be measured rather than trusted.

    `desk.position()` is what `engine.authority_for` consults, and it is the one
    place the proposed/ratified distinction turns into behaviour."""
    desk = record.load(CORPUS)
    served = 0
    for q in _positions():
        found = desk.position(q.citation)
        if q.proposed:
            assert found is None or found.id != q.id, (
                f"{q.id} is a proposal and is being served")
        else:
            assert found is not None and found.id == q.id, (
                f"{q.id} is ratified and is not being served")
            served += 1
    assert served == len(RATIFIED), (
        f"{served} positions are served; the roster holds {len(RATIFIED)}")


def test_the_record_holds_no_proposal_at_all_and_that_is_said_out_loud():
    """THE HALF OF THIS FILE THAT IS CURRENTLY EXERCISING NOTHING.

    Every one of the twenty positions on file is ratified, and that was already
    true before the merge — checked against the seven records on 10 September
    2026, which held twenty positions and no proposal between them. So the
    `if q.proposed` branch above, and
    `test_guards.py::test_a_proposal_does_not_answer_on_any_shipped_desk`, run
    over an empty set and pass without looking at anything.

    That is a fact about the record rather than a defect in the checks, and the
    right response is to state it where somebody reading a green suite can see
    it — not to quietly rely on branches nothing enters. The behaviour itself is
    exercised on constructed records in `test_record.py`.
    """
    proposals = [q.id for q in _positions() if q.proposed]
    assert proposals == [], (
        "a proposal is on file — good: the branches above now have something "
        "to be true of. Delete this test and say so in the commit.")
