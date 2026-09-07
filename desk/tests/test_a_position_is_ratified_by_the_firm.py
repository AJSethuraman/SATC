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
from conftest import DESKS                                  # noqa: E402

#: Every position the firm has ratified, and the day they did it. Adding a line
#: here is the act of recording a decision, so it belongs in the same commit as
#: the `Ratified:` field it describes and in no other.
RATIFIED = {
    ("capitalization-and-de-minimis", "POS3"): "5 September 2026",
    ("cash-and-bank", "POS1"): "5 September 2026",
    ("cash-and-bank", "POS2"): "5 September 2026",
    ("meals-and-entertainment", "POS1"): "5 September 2026",
    ("meals-and-entertainment", "POS2"): "5 September 2026",
    ("meals-and-entertainment", "POS3"): "5 September 2026",
    ("meals-and-entertainment", "POS4"): "5 September 2026",
    ("personal-or-business", "POS2"): "5 September 2026",
    ("personal-or-business", "POS3"): "5 September 2026",
    # Ratified on the second docket and REWORDED on the fourth, 6 September
    # 2026, on the firm's instruction ("Reword POS2"). The reword is recorded on
    # the position itself; the ratification date is the day they first said yes.
    ("rewards-and-information-returns", "POS2"): "5 September 2026",
    # THE FOURTH DOCKET'S ONLY RATIFICATION, and this roster is what surfaced it
    # as a decision rather than a diff. Answered "Ratify it", unamended, with no
    # note — against a recommendation to narrow it, which the firm declined.
    ("rewards-and-information-returns", "POS1"): "6 September 2026",
    # THE FIFTH DOCKET'S ONLY RATIFICATION, answered 2026-09-07T01:38Z. The firm
    # pressed "Ratify it" with no note, on a position the docket recommended
    # ratifying. It sat unbuilt for two hours because this session did not read
    # the form back — see `docs/DECISIONS-2026-09-07.md`.
    ("personal-or-business", "POS1"): "7 September 2026",
    # THE SIXTH DOCKET'S THREE, answered 2026-09-07 13:09-13:10Z. The two
    # capitalization positions had been held twice for a reason the firm then
    # removed themselves — they added the field the follow-up needed. The
    # rewards position was ratified with its wording still owed a redraft
    # (matter `dec-register`), which is a change to how it READS and not to
    # what it says.
    ("capitalization-and-de-minimis", "POS1"): "7 September 2026",
    ("capitalization-and-de-minimis", "POS2"): "7 September 2026",
    ("rewards-and-information-returns", "POS3"): "7 September 2026",
    ("vehicle-expense", "POS1"): "5 September 2026",
    ("vehicle-expense", "POS2"): "5 September 2026",
    ("vehicle-expense", "POS3"): "5 September 2026",
    ("vehicle-expense", "POS4"): "5 September 2026",
    ("vehicle-expense", "POS5"): "5 September 2026",
}


def _positions():
    for d in sorted(DESKS.iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        desk = record.load(d)
        for q in desk.positions:
            yield desk.name, q


def test_nothing_is_ratified_that_is_not_on_the_roster():
    live = {(name, q.id) for name, q in _positions() if not q.proposed}
    new = live - set(RATIFIED)
    assert not new, (
        f"{sorted(new)} is served as the firm's own word and is not on the "
        f"roster. A position the firm never ratified, served verbatim, is the "
        f"worst thing this record can hold. If they did say yes, add it here "
        f"with the date they said it — in this commit, not a later one."
    )


def test_the_roster_does_not_outlive_what_it_describes():
    live = {(name, q.id) for name, q in _positions() if not q.proposed}
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
    for name, q in _positions():
        if q.proposed:
            continue
        when = RATIFIED[(name, q.id)]
        assert when in q.ratified, (
            f"{name}/{q.id} is rostered as ratified on {when}; its own "
            f"Ratified line says {q.ratified[:80]!r}")
        assert re.search(r"\bfirm\b", q.ratified, re.I), (
            f"{name}/{q.id} does not say the firm ratified it: "
            f"{q.ratified[:80]!r}")


def test_a_proposal_is_never_served():
    """The consequence, stated where it can be measured rather than trusted.

    `desk.position()` is what `engine.authority_for` consults, and it is the one
    place the proposed/ratified distinction turns into behaviour."""
    served = 0
    for name, q in _positions():
        found = record.load(DESKS / name).position(q.citation)
        if q.proposed:
            assert found is None or found.id != q.id, (
                f"{name}/{q.id} is a proposal and is being served")
        else:
            assert found is not None and found.id == q.id, (
                f"{name}/{q.id} is ratified and is not being served")
            served += 1
    assert served == len(RATIFIED), (
        f"{served} positions are served; the roster holds {len(RATIFIED)}")
