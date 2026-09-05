"""What the firm does where authority allows a choice.

THE DIVISION THIS FILE EXISTS FOR. `extracted/` holds authority — someone else's
words, checkable line by line against a public source, which is why an agent may
write it and why a forty-five-entry diff can be skimmed. `positions/` holds
judgement. An agent only ever PROPOSES here, and the pull request is the firm's
yes.

Keeping them in separate stores is not tidiness. A large extraction diff gets
skimmed and a one-position diff gets read, and if a position could ride along
inside an extraction it would be ratified by a glance. `guards.py` fails the
build rather than trusting anyone to notice.

WHY THIS MATTERS MORE THAN IT LOOKS. Some authority cannot be read by a desk at
all — FASB ASC's licence forbids the content reaching a model by any route. For
those sources a position IS the desk's entire knowledge: the firm reads the
authority in their own session, decides, and writes it here in their own words.
The citation points at the paragraph; whoever wants the text opens it themselves.
That is a better artifact than an ingested one, because what goes to a client
should be the firm's position with the paragraph behind it, never someone else's
prose filtered through a model.

HOW A POSITION IS WORDED, WHICH IS NOT HOW A CONVICTION IS WORDED. The firm, on
the docket of 5 September 2026, ratifying thirteen of these: *"I want to ensure
that where when you say my words, they're not the direct quotes I do like the
convictions and stuff, including direct quotes, so we can kind of remember where
they came from but positions that the agent finds to argue from should be
cleaned up."* And on one of them: *"I don't want our desk to have this much like
of my thought behind it."*

So a conviction in `canon` keeps the quotation, because its provenance IS its
authority. A POSITION IS CLEANED UP: the `Position` line and the `Ratified` line
are prose the desk can hand to an answerer, and the firm's own words for it live
in the log (`docs/DECISIONS-WAITING-*.md`), where provenance belongs. Pasting a
spoken answer in here reads as the firm's considered wording when it was a
thought in passing, and it is what `serve()` returns verbatim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from record import RecordError, _blocks, _date, _field, _inline

_HEAD = re.compile(r"^## (\S+) · (.+)$", re.M)

#: The fields that make a block a position rather than a passage. `guards.py`
#: refuses to find any of these under `extracted/`.
MARKERS = ("Position", "Ratified")


@dataclass(frozen=True)
class Position:
    """One thing the firm decided, in the firm's words, with its authority."""
    id: str
    title: str
    citation: str
    recorded: str
    position: str
    why: str = ""
    ratified: str = ""
    #: The facts about the ENGAGEMENT this position cannot be applied without,
    #: from `record.Context.FACTS`. Optional, and empty on almost every position.
    #:
    #: WHY A POSITION AND NOT A DESK. The firm's objection was about one rule,
    #: not one desk: a Home Depot charge needs the client's trade because the
    #: VENDOR test says the item and the profession decide. The desk's other
    #: positions -- a cleaning service, a home office -- do not turn on it. Made
    #: desk-wide, this would have refused every problem on the desk whose worked
    #: example never states a trade, which is a measured score thrown away to
    #: enforce a rule those questions do not use.
    #:
    #: NARROWING ONLY, LIKE `answered_by`. A position that declares nothing
    #: behaves exactly as it did, so the cost of the new gate can only ever be
    #: paid by a position that opted into it.
    needs: tuple = ()

    @property
    def proposed(self) -> bool:
        """Not yet ratified. Real until a person merges it, and not before."""
        return not self.ratified


def _needs(listed: str, where: str) -> tuple:
    """The recorded facts this position cannot be applied without.

    Only split here. WHICH names are legal is the desk's own declaration and is
    checked in `record.load`, where the desk is in hand -- a check in this file
    would have to name the facts, and this file is shared by every desk.
    """
    return tuple(t.strip().lower() for t in listed.split(",") if t.strip())


def parse(text: str) -> list[Position]:
    out = []
    for head, block in _blocks(text, _HEAD):
        pid, title = head.group(1), head.group(2).strip()
        where = f"position {pid}"
        out.append(Position(
            id=pid,
            title=title,
            citation=_inline(block, "Citation", where),
            recorded=_date(_inline(block, "Recorded", where), "recorded", where),
            position=_field(block, "Position", where),
            why=_field(block, "Why", where, required=False),
            ratified=_field(block, "Ratified", where, required=False),
            needs=_needs(_field(block, "Needs", where, required=False), where),
        ))
    return out


PREAMBLE = """# Positions — what the firm does where the rules permit a choice

**An agent proposes here. It never writes.** The pull request is the firm's yes,
and a position that entered any other way is one they will disown the moment it
is read back at them.

Each entry carries the firm's **own words**, the authority it rests on, and the
date. Where a source cannot be read by a desk at all — a licence forbidding the
content reaching a model — a position here is the desk's entire knowledge of it,
and the citation is how a reader gets to the text themselves.

---

"""
