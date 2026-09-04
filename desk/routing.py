"""Which desk a question belongs to. A lookup, never a judgement.

TWO PATHS IN, AND THE SECOND IS THE ONE THAT MATTERS.

  1. A doer asks, because it is unsure.
  2. The engine refuses an out-of-authority act and NAMES the desk.

The second is reliable because it does not depend on a model recognising its own
ignorance -- which is the weakest link in any design that has one. This session
watched the weaker mechanism fail in the same repository: canon installed
successfully and its standing behaviour still did not load, and `how-we-work`
already documents that "what is available is not the same as what is loaded".

ONE TOOL SCHEMA IN THE CALLER, NOT ONE PER DESK. LOCAL-LLM-PATTERN rule 1: 8 GB
of VRAM is an 8,192-token window, and "loading every tool schema (~11k tokens)
silently truncates the model's own instructions -- it then 'ignores' rules it
never received." So the caller holds `ask_desk` and the router resolves the rest
server-side, where it costs nothing.

NO MODEL DECIDES WHICH DESK TO USE. "Does this question touch the subject this
desk is about" is a comparison, not a judgement -- which is C8's test, and the
reason this stays deterministic.

SILENCE IS A RESULT. A question matching no desk returns nothing: not a nearest
guess, not a note. A router that always answers is one whose answer means
nothing, and canon's own challenge module draws the same line for the same
reason.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from _canon import load_record
from record import RecordError, _blocks

_HEAD = re.compile(r"^## (\S+) · (.+)$", re.M)


@dataclass(frozen=True)
class Registration:
    """One desk, and the subjects that bring it into play."""
    desk: str
    title: str
    fires_on: tuple[str, ...]


def parse_subjects(text: str, desk_name: str) -> Registration:
    blocks = _blocks(text, _HEAD)
    if not blocks:
        raise RecordError(f"{desk_name}: SUBJECTS.md declares no desk")
    head, block = blocks[0]
    # NOT `.*?$`. Canon's own field reader takes a single line, which is right
    # there because its fields are short -- but this list is long enough to wrap,
    # and a single-line read of a wrapped value truncates it SILENTLY. Written
    # that way first, this parsed 5 subjects out of 30 and reported success.
    m = re.search(r"^\*\*Fires on:\*\*[ ]?(.*?)(?=\n\n|\n\*\*|\Z)",
                  block, re.M | re.S)
    if not m or not m.group(1).strip():
        raise RecordError(
            f"{desk_name}: no 'Fires on' subjects. A desk nothing routes to is "
            f"a desk nobody asks."
        )
    # THE DIRECTORY IS THE IDENTITY. A typo or stale name in the heading became
    # `Registration.desk`, so routing still matched while
    # `refusal_naming_the_desk()` sent the caller to a desk that does not exist
    # -- the deterministic recovery path pointing away from the record that
    # produced it. Refuse the mismatch rather than pick a winner.
    if head.group(1) != desk_name:
        raise RecordError(
            f"{desk_name}/SUBJECTS.md registers itself as {head.group(1)!r}; a "
            f"desk named differently from its directory cannot be reached by "
            f"the name a refusal gives out"
        )
    return Registration(
        desk=head.group(1),
        title=head.group(2).strip(),
        fires_on=tuple(
            t.strip().lower()
            for t in " ".join(m.group(1).split()).split(",")
            if t.strip()
        ),
    )


def registry(desks_dir: Path) -> list[Registration]:
    out = []
    for d in sorted(Path(desks_dir).iterdir()):
        f = d / "SUBJECTS.md"
        if f.is_file():
            out.append(parse_subjects(f.read_text(encoding="utf-8"), d.name))
    return out


def route(question: str, registrations: list[Registration]) -> list[Registration]:
    """Every desk whose subjects the question touches. Possibly none."""
    touches = load_record().touches
    return [r for r in registrations
            if any(touches(question, term) for term in r.fires_on)]


def refusal_naming_the_desk(question: str, registrations: list[Registration]) -> str:
    """What the engine says when it stops a doer. Never a bare "no".

    On a small model a refusal that only says no ends the run; one that names the
    right next step self-corrects it (LOCAL-LLM-PATTERN rule 3).
    """
    hits = route(question, registrations)
    if not hits:
        return ""
    named = ", ".join(f"{r.desk} ({r.title})" for r in hits)
    return (f"this is a judgement outside your authority. Ask {named} with "
            f"ask_desk, then come back with the citation.")
