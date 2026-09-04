"""Taxpayer identification numbers, refused where they arrive.

`CLAUDE.md` says: *"Validation tests fail the build if legal names / full TINs
leak into outputs."* For legal names that is true. For TINs it was true of
`samples/*.json` and of nothing else -- the shape regex existed in one test and
ran over fixtures, so the constraint held because nobody had typed one, not
because anything stopped them.

WHERE ONE ACTUALLY GETS IN. Not through a field: no field may be named for a
TIN and a test enforces that. Through FREE TEXT, which no schema can constrain
-- the interview's working notes, "what changed since last year", the close-out
note a preparer writes with the filed return open in Drake, and the website's
"anything else we should know?", which lands verbatim in the leads workbook on
OneDrive. Five inlets, and the pre-send gate would have passed a number pasted
into a client's name straight onto a document a client reads.

THE SHAPE, AND WHY THESE TWO. `123-45-6789` is an SSN or an ITIN;
`12-3456789` is an EIN. Both were measured against every rendered document,
sample, registry and template in the repository -- 302 files, zero matches --
before this was allowed to block anything. A guard that cries wolf gets muted,
and then it is worse than nothing.

WHAT THIS IS NOT. Nine digits with no dashes is not matched, and deliberately:
a bare `123456789` is indistinguishable from an account number, a case
reference or a phone number typed without punctuation, and blocking on it would
fire on real work. This catches the formatted shape a person types when they
are copying off a return, which is the case that actually happens.

NOTHING HERE EVER ECHOES THE VALUE. A refusal that quotes the number it
objected to has written the number into a log, a terminal scrollback and a
screenshot -- which is the leak, one step further along. Every message names
WHERE it was found and says nothing about what.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# An SSN or ITIN as a person types it, and an EIN as a person types it.
SHAPES = (
    ("an SSN or ITIN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("an EIN", re.compile(r"\b\d{2}-\d{7}\b")),
)


@dataclass(frozen=True)
class Found:
    """One identifier-shaped value, described without being repeated.

    `where` is a field name, a document name, a path -- whatever the caller
    knows. `kind` says which shape matched, so a preparer can tell "the EIN you
    pasted" from "the SSN you pasted" without either being printed back.
    """
    where: str
    kind: str

    def line(self) -> str:
        return f"{self.where} holds something shaped like {self.kind}"


def find(value, where: str = "") -> list[Found]:
    """Every identifier-shaped run inside `value`, however it is nested.

    Walks dicts and lists, because the things being checked are answer records
    and the leak is in a free-text answer several levels down. A dict's KEYS are
    walked as well as its values: a key is preparer-typed in exactly one place
    that matters -- nothing today does it, and the day something does, this
    should already be looking.
    """
    out: list[Found] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            here = f"{where}.{key}" if where else str(key)
            out += find(str(key), here) if _shaped(str(key)) else []
            out += find(inner, here)
        return out
    if isinstance(value, (list, tuple)):
        for i, inner in enumerate(value):
            out += find(inner, f"{where}[{i}]" if where else f"[{i}]")
        return out
    if value is None or isinstance(value, bool):
        return out

    text = value if isinstance(value, str) else str(value)
    for kind, shape in SHAPES:
        if shape.search(text):
            out.append(Found(where=where or "(the value)", kind=kind))
    return out


def _shaped(text: str) -> bool:
    return any(shape.search(text) for _, shape in SHAPES)


class TinRefused(ValueError):
    """Raised where a TIN-shaped value would have been written down.

    A `ValueError` rather than a bespoke hierarchy: every caller here already
    reports one, and a refusal nobody catches should still stop the write.
    """


def refuse(value, what: str) -> None:
    """Stop the write, name the field, print nothing.

    `what` is what is being written -- "the interview answers", "the close-out
    record" -- so the message reads as a sentence rather than a stack trace.
    """
    found = find(value)
    if not found:
        return
    where = "; ".join(f.line() for f in found[:6])
    more = f", and {len(found) - 6} more" if len(found) > 6 else ""
    raise TinRefused(
        f"{what} was not written: {where}{more}.\n\n"
        f"Identification numbers belong in Drake and in satc_system's "
        f"encrypted vault, never in this record -- it lives in OneDrive, and "
        f"it is read back every season. Take the number out of that answer and "
        f"try again. Nothing else about the sitting is lost.\n\n"
        f"If the client genuinely needs to be identified here, the last four "
        f"digits are enough for every document in the pack."
    )
