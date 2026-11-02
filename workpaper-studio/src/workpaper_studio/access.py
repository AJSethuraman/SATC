"""Access the organization defines: its own levels, what each may do, and who holds which.

The owner, 2 Nov 2026: "i like the idea of having users but it should be definable by the organization for what each
level of access can actually do". So the list of things a person can do is fixed (the software has to know what an
action is) and everything about who may do them is the organization's.

Two rules are not the organization's to remove, because they are what makes the record worth trusting:
  1. nobody reviews or approves work they entered, and nobody approves a tool they proposed;
  2. every action is kept in the log.
An organization can add strictness (a second person to confirm a limit) but cannot take these away.
"""
from __future__ import annotations

ACTIONS = {   # key: what it lets a person do, in the words the screens use
    "start_case": "start a case",
    "enter": "enter and change a case's answers",
    "submit": "send a case for review",
    "answer_point": "answer a review point",
    "record_exception": "record an exception beside a result",
    "raise_point": "raise a review point",
    "clear_point": "clear a review point",
    "return": "return a case to its preparer",
    "acknowledge": "acknowledge an exception",
    "approve": "approve a case",
    "release": "release a case",
    "see_all": "see every case, not only their own",
    "load_work": "load the work list from the master database",
    "propose_tool": "propose a tool for publishing",
    "approve_tool": "approve a tool",
    "set_limits": "set the organization's limits",
    "manage_access": "change levels and who holds them",
}
RULES = {"two_person_limits": "A limit needs a second person to confirm it"}

DEFAULT = {
    "levels": {
        "Preparer": ["start_case", "enter", "submit", "answer_point", "record_exception"],
        "Reviewer": ["raise_point", "clear_point", "return", "acknowledge", "approve", "release", "see_all"],
        "Tool designer": ["propose_tool"],
        "Tool approver": ["approve_tool"],
        "Admin": ["set_limits", "manage_access", "load_work", "release", "see_all"],
    },
    "people": {
        "A. Rivera": ["Preparer"],
        "J. Moss": ["Preparer"],
        "D. Patel": ["Reviewer"],
        "K. Owens": ["Reviewer", "Tool approver"],
        "M. Okafor": ["Tool designer", "Admin"],
    },
    "rules": {"two_person_limits": False},
}


def check(body):
    """Refuse an access set that is not coherent, in words an admin can act on."""
    levels, people = body.get("levels") or {}, body.get("people") or {}
    if not levels:
        raise ValueError("There must be at least one level.")
    for lv, acts in levels.items():
        if not lv.strip():
            raise ValueError("A level needs a name.")
        bad = [a for a in acts if a not in ACTIONS]
        if bad:
            raise ValueError(f"Level {lv!r} names an action that does not exist: {bad[0]}.")
    for p, lvs in people.items():
        if not p.strip():
            raise ValueError("A person needs a name.")
        bad = [lv for lv in lvs if lv not in levels]
        if bad:
            raise ValueError(f"{p} holds a level that does not exist: {bad[0]}.")
    holders = [p for p, lvs in people.items() if any("manage_access" in levels[lv] for lv in lvs)]
    if not holders:
        raise ValueError("Nobody would be left able to change access. Keep at least one person with that.")
    for r in body.get("rules") or {}:
        if r not in RULES:
            raise ValueError(f"Unknown rule {r!r}.")
    return body


def actions_of(body, person):
    return {a for lv in body["people"].get(person, []) for a in body["levels"].get(lv, [])}
