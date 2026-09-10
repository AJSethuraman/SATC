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

#: WHAT A POSITION RESTS ON.
#:
#: `dec-pos2`, 10 September 2026 — the firm: **"Firm policy, no citation — with
#: two conditions."** POS11 (*"flag it for attention and ask the client what was
#: bought; do not book it to owner draws on the seller's name"*) is pinned to
#: § 1.262-1(a), and two independent judges refused it: that paragraph is about
#: costs which are PERSONAL, and the position is about costs whose nature is
#: UNKNOWN. The position is sound and the pin is wrong.
#:
#: A pin that is wrong is worse than no pin. It tells a reader the regulation
#: says something it does not, and it survives every check in this repository
#: because the citation resolves. So a position may now say that it rests on the
#: firm rather than on a paragraph — and saying so is the whole of what makes it
#: different from a mis-pinned one.
AUTHORITY = "authority"      #: rests on a paragraph, cited
FIRM_POLICY = "firm policy"  #: rests on the firm, cited to nothing
KINDS = (AUTHORITY, FIRM_POLICY)

#: THE FIRST OF THE FIRM'S TWO CONDITIONS, in their words:
#:
#:     "I'm good with this but can I want this to be clearly marked as they may
#:      need to be reviewed/changed at some point."
#:
#: `open` is the state every firm-policy position starts in and it is NOT a
#: defect — it is the mark. What it must never do is default silently: a policy
#: that has never been looked at and one that was looked at last week are
#: different facts, and only one of them may be served without saying so.
OPEN = "open"


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
    #: `authority` or `firm policy` — see `KINDS`. Absent means `authority`,
    #: which is what every position in the record was before `dec-pos2`, so
    #: adding the field changed no existing position's behaviour.
    kind: str = AUTHORITY
    #: `open`, or what a reviewer found and when. The firm's first condition.
    #: Only meaningful on a `firm policy` position; `record.load` refuses it
    #: elsewhere rather than letting it read as a general review log.
    reviewed: str = OPEN
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
    #: The client-level rules that would DISPLACE this position, from the same
    #: vocabulary as `needs` -- except that this one may name a fact the desk
    #: does not record, and that asymmetry is the whole feature.
    #:
    #: `Needs:` says "I cannot be applied without this", and `record.load`
    #: refuses one naming an undeclared fact, because such a position could
    #: never be served by anybody.
    #:
    #: `Unless:` says "I am the firm's default, and it holds unless the file
    #: says this client is different". A fact the desk does not record is not an
    #: error here -- it is the FINDING. The firm, holding three positions on
    #: 6 September 2026: *"if the follow up has no answer we know there's a legit
    #: hole to fix because the accountant or firm never assigned it up front ...
    #: What if this mattered only sometimes and we never even made a field for
    #: it."* A position that may only ask about fields somebody already thought
    #: to create can never discover the one nobody thought to create.
    unless: tuple = ()

    @property
    def proposed(self) -> bool:
        """Not yet ratified. Real until a person merges it, and not before."""
        return not self.ratified

    @property
    def is_policy(self) -> bool:
        """The firm's own rule, resting on no paragraph."""
        return self.kind == FIRM_POLICY

    @property
    def unreviewed(self) -> bool:
        """A firm policy nobody has checked against the authority on file.

        THE FIRM'S SECOND CONDITION, and it is the risk that arrives with the
        approval:

            "I would also be remiss if something I said is my position blatantly
             goes against a regulation or something. I would want the option to
             review that too though"

        An uncited position is exactly the kind that can sit against authority
        with nothing noticing — there is no citation for anything to check it
        with. So it needs the INVERSE of a citation check: not *what proves
        this* but *does anything on file contradict this*, with the answer going
        to the firm. `positions.against` assembles what a reviewer must read;
        this says whether anybody has.
        """
        return self.is_policy and self.reviewed.strip().lower() == OPEN


#: A fact name: lowercase words joined by underscores, and nothing else. Not a
#: style rule -- the SHAPE is what makes a swallowed paragraph fail loudly.
_FACT = re.compile(r"^[a-z][a-z0-9_]*$")


def _needs(listed: str, where: str, field: str = "Needs") -> tuple:
    """The facts named on a `Needs:` or `Unless:` line.

    Only split and shape-checked here. WHICH names are legal is the desk's own
    declaration and is checked in `record.load`, where the desk is in hand -- a
    check in this file would have to name the facts, and this file is shared by
    every desk.

    THE SHAPE CHECK EXISTS BECAUSE THE FIELD READER IS GREEDY, and the failure
    was silent. `_field` reads to the next `**Marker:**`, so a paragraph of
    explanation written under an `Unless:` line and above `**Why:**` is read as
    part of the value -- and this function then split that paragraph on its
    commas and returned eight "facts", one of them ending in a quotation mark.
    Measured 6 September 2026: the desk loaded, every test passed, and the
    position was asking about a fact called `right?" — and on the threshold
    below`. A field that was mis-read and a field that was correct looked
    identical downstream, which is the failure this record's own preamble is
    written against.
    """
    out = []
    for token in listed.split(","):
        name = token.strip().lower()
        if not name:
            continue
        if not _FACT.match(name):
            raise RecordError(
                f"{where}: {field} names {name.splitlines()[0][:60]!r}, which is "
                f"not a fact name. It must be lowercase words joined by "
                f"underscores. A comma or a line of prose under this field is "
                f"read as part of it — put the explanation under **Why:**.")
        out.append(name)
    return tuple(out)


def _kind(value: str, where: str) -> str:
    """`authority` unless the block says otherwise, and never a guess.

    A MISSPELT KIND MUST NOT FALL BACK TO `authority`, which is the one way this
    field can do harm: a position meaning to say it rests on the firm would
    silently claim to rest on the paragraph in its `Citation:` line — the exact
    mis-pin `dec-pos2` exists to stop, reintroduced by a typo.
    """
    value = " ".join(value.split()).lower()
    if not value:
        return AUTHORITY
    if value not in KINDS:
        raise RecordError(
            f"{where}: Kind says {value!r}; it may say "
            f"{' or '.join(repr(k) for k in KINDS)}. A misspelt kind would "
            f"leave a position claiming the authority of a paragraph it does "
            f"not rest on, which is what this field exists to stop.")
    return value


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
            kind=_kind(_field(block, "Kind", where, required=False), where),
            reviewed=(_field(block, "Reviewed", where, required=False).strip()
                      or OPEN),
            needs=_needs(_field(block, "Needs", where, required=False), where),
            unless=_needs(_field(block, "Unless", where, required=False), where,
                          "Unless"),
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

