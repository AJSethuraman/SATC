"""Refused, but kept — the queue that turns a refusal into a work item.

A refusal is a FINDING, and throwing away the reasoning behind it destroys the
finding. The engine refuses to *serve* an uncited answer; it does not delete it.

WHY THIS EXISTS AT ALL. An answer the desk could not support is usually telling
you one of two useful things: that real authority exists and was never loaded, or
that the rules permit a choice and nobody has taken one. From outside those look
identical, and only the reasoning tells them apart. Without this queue the desk's
failures are a number that goes down for reasons nobody can inspect.

THREE RESOLUTIONS, NONE AUTOMATIC, ALL BY PULL REQUEST:

  real authority never loaded  -> promote to a SOURCE
  a defensible call the rules do not settle -> promote to a POSITION, in the
                                               firm's own words
  nowhere to write the answer  -> build the FIELD, naming the position that
                                  asked for it
  an invention                 -> leave it. its visibility IS the finding.

THE SIXTH IS THE FIRM'S, 7 SEPTEMBER 2026, AND IT IS THE ONLY ONE THAT CHANGES
THE SOFTWARE. They put it: *"it's similar to the desk saying hey you should have
X info - and either way we probably should… that seems low stakes and required
and i would approve it fairly easily, but maybe approvals based on desk feedback
for coding updates?"* They then took the recommendation: **a field, and only a
field.** Somewhere to record a fact is additive, reversible and invisible to a
client -- the worst case is an empty column nobody fills. A step in the close
changes what a person does every time, and that stays a decision.

AND IT ARRIVES CARRYING ITS CHAIN. `needs_field` never appears without
`asked_by`: a desk asks for a field because a POSITION it holds names a fact, so
approving the field is approving that position's reach. `from_refusal` copies
both off the refusal, where `engine` sets them as fields rather than leaving them
to be read back out of a sentence.

**Retained is not accepted.** An entry here is never returned to a caller and
never counted as correct. That boundary is the whole reason keeping it is safe,
and `test_unsupported.py` asserts it rather than trusting this paragraph.

This is `canon-mine`'s discipline applied to answers instead of convictions:
propose, never write.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from record import (RecordError, _blocks, _date, _field, _inline,
                    under as record_under)

_HEAD = re.compile(r"^## (\S+) · (.+)$", re.M)

#: What an EMPTY citation looks like on the page, in ONE place because render
#: and parse both need it and two copies of a sentinel drift. Written literally
#: in `render` and not recognised by `parse`, an entry with no citation came
#: back carrying the words "(none offered)" as its citation -- so
#: `_same_refusal`, which compares that field, stopped matching the entry it had
#: just written, and the idempotency guard would file the same finding twice.
NO_CITATION = "(none offered)"

#: WHAT A QUESTION MAY FAIL FOR, and the reason this is a closed set rather than
#: a string. `failed_because` is one of only two fields `render` writes into
#: Markdown structure UNESCAPED, and the docstring there says why that is safe:
#: it is a closed vocabulary. `from_refusal` gets it from the engine, which
#: validates. `from_question` is a NEW front door that took it from a caller
#: with a default and no check, so the premise the escape rule rests on stopped
#: being true the moment that function was added -- `because="authority_absent\n
#: ## U99 · injected"` writes a queue `parse()` then refuses to read, and an
#: ordinary typo files the entry under a category nothing counts.
#:
#: It is the two a question can honestly be in. The rest of `engine.REASONS`
#: describe an ANSWER that was tried -- uncited, unsupported, contradicted --
#: and a question has not been answered. `test_unsupported` proves this is a
#: subset of the engine's set, so the two cannot drift apart.
QUESTION_REASONS = ("authority_absent", "facts_not_established",
                    "document_not_requested")


@dataclass(frozen=True)
class Unsupported:
    """One answer the engine would not serve, kept with its reasoning."""
    id: str
    question: str
    concluded: str
    believed_authority: str
    failed_because: str
    recorded: str
    model: str = ""
    working: str = ""
    #: A citation THIS DESK HOLDS that contains the one the answer offered --
    #: empty when it reached outside the desk's authority altogether. See
    #: `from_refusal` for why the queue records it.
    falls_under: str = ""
    #: THE FOLLOW-UP, when the refusal had one: a question a preparer can act on.
    #:
    #: The firm, 6 September 2026: *"it can ask a follow up and if the follow up
    #: has no answer we know there's a legit hole to fix because the accountant
    #: or firm never assigned it up front. This is also a way to check for bugs
    #: or defects while agents perform real work."* That last sentence is why it
    #: belongs HERE and not only in the reply: this queue is where the holes
    #: accumulate, and a question that reached one caller and no file is a hole
    #: found and then dropped.
    #:
    #: It names a field and never a value -- this file lives in the repository.
    asked: str = ""
    #: THE FACT THAT HAS NOWHERE TO LIVE, and THE POSITION THAT ASKED FOR IT.
    #: Set together or not at all -- see the sixth resolution in this file's
    #: preamble. A field request without the position behind it is an ask the
    #: firm cannot check, and checking it is the whole condition they approved
    #: it under.
    needs_field: str = ""
    asked_by: str = ""

    @property
    def near_miss(self) -> bool:
        """The desk reached a finer point inside its own authority.

        Not a resolution and not a pass: the entry stays in the queue and is
        still never served. It is a label on WHICH KIND of refusal this is, so
        the queue can be read.
        """
        return bool(self.falls_under)

    def render(self) -> str:
        """The exact text stored. Written so a person can read the diff.

        EVERY FIELD HERE COMES FROM OUTSIDE, AND EVERY ONE OF THEM IS ESCAPED.
        `working` was quoted first, on the reasoning that it was "the one
        free-form field". It was not. The question is the caller's, and the
        conclusion and citation are the MODEL's -- all three arbitrary text, all
        three written straight into Markdown structure. A conclusion containing
        `**Evidence:** ...` was read as the next field and silently truncated
        what followed; a question containing a line starting `## U99 · ` was read
        as another ENTRY and made the file unparsable. The escape was applied to
        an instance instead of to the category, which is the same mistake this
        pull request has now made four times.

        Only `failed_because` (a closed vocabulary) and `recorded` (a date the
        parser validates) are safe unescaped, because neither can be arbitrary.
        """
        lines = [
            f"## {self.id} · {_oneline(self.question)}",
            "",
            f"**Failed because:** {self.failed_because} · **Recorded:** {self.recorded}",
            "",
            "**Question:**", "", *_quote(self.question),
            "",
            "**Concluded:**", "", *_quote(self.concluded),
            "",
            "**Believed authority:**", "",
            *_quote(self.believed_authority or NO_CITATION),
        ]
        if self.falls_under:
            lines += ["", f"**Falls under:** {_oneline(self.falls_under)}"]
        if self.asked:
            lines += ["", f"**Asked:** {_oneline(self.asked)}"]
        if self.needs_field:
            # TWO STANDALONE FIELDS, not one line with a separator. `Failed
            # because · Recorded` gets away with sharing a line because both are
            # closed vocabularies the parser validates; a fact name and a
            # position id are neither, and `_inline` has no optional form.
            lines += ["", f"**Needs field:** {_oneline(self.needs_field)}",
                      "", f"**Asked by:** {_oneline(self.asked_by)}"]
        if self.model:
            lines += ["", f"**Model:** {_oneline(self.model)}"]
        if self.working:
            lines += ["", "**Working:**", "", *_quote(self.working)]
        return "\n".join(lines) + "\n"


def parse(text: str) -> list[Unsupported]:
    out = []
    for head, block in _blocks(text, _HEAD):
        uid = head.group(1)
        where = f"unsupported {uid}"
        # Read from the quoted bodies, never from the heading. The heading is a
        # one-line LABEL so a person can scan the file; the field beneath it is
        # the value, and it is the value that must survive the round trip.
        out.append(Unsupported(
            id=uid,
            question=_quoted(block, "Question", where),
            failed_because=_inline(block, "Failed because", where),
            recorded=_date(_inline(block, "Recorded", where), "recorded", where),
            concluded=_quoted(block, "Concluded", where),
            believed_authority=_uncite(_quoted(block, "Believed authority", where)),
            falls_under=_field(block, "Falls under", where, required=False),
            asked=_field(block, "Asked", where, required=False),
            needs_field=_field(block, "Needs field", where, required=False),
            asked_by=_field(block, "Asked by", where, required=False),
            model=_field(block, "Model", where, required=False),
            working=_quoted(block, "Working"),
        ))
    return out


def _uncite(value: str) -> str:
    """The sentinel back to the empty string it stands for. See `NO_CITATION`."""
    return "" if value.strip() == NO_CITATION else value


def _oneline(value: str) -> str:
    """A heading is one line. Collapse rather than let it break the format."""
    return " ".join(value.split())


def _quote(value: str) -> list[str]:
    """Escape arbitrary text into lines that cannot be read as structure."""
    return [f"> {ln}" if ln else ">" for ln in value.split("\n")]


def _quoted(block: str, label: str, where: str = "") -> str:
    """Read a `>`-quoted free-form value back, exactly as it was written."""
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*[ \t]*$", block, re.M)
    if not m:
        if where:
            raise RecordError(f"{where}: no '{label}' field")
        return ""
    out = []
    for line in block[m.end():].split("\n"):
        if line.startswith("> "):
            out.append(line[2:])
        elif line.rstrip() == ">":
            out.append("")
        elif not line.strip() and not out:
            continue                         # the blank line after the label
        else:
            break
    return "\n".join(out)


PREAMBLE = """# Unsupported — what the desk could not answer, kept with the reasoning

**Retained is not accepted.** Nothing here was returned to a caller and nothing
here is counted as correct. It is kept because a refusal is a finding, and the
reasoning behind it is the best evidence of what this desk's record is missing.

Two things land here and they read differently. An **answer the engine refused**
carries what was concluded and what it cited. A **question nobody has answered**
— an agent that stopped mid-close and wrote down what it needed — carries no
conclusion at all, and `Concluded` says so rather than being left blank.

Six resolutions, none automatic, all by pull request:

| What the reasoning shows | Resolution |
|---|---|
| Real authority that was never loaded | promote to a **source** |
| A defensible call the rules do not settle | promote to a **position**, in the firm's words |
| The rule is clear and a FACT is missing | **ask the client.** No amount of authority closes it |
| A named DOCUMENT settles it and nobody asked | **request it** — raised to the preparer, never to the client |
| The rule is clear and there is NOWHERE to write the answer | **build the field**, naming the position that asked |
| An invention | leave it. Its visibility *is* the finding |

A queue that only grows is a desk nobody is feeding.

---

"""


#: Where the preamble stops and the entries start. The entries are `## ` blocks,
#: so the first one is the boundary; a queue with none is all preamble.
_FIRST_ENTRY = "\n## "


def _refreshed(text: str) -> str:
    """The queue's own preamble, brought up to date with the code.

    IT WAS WRITTEN ONCE AND NEVER AGAIN, and that made the firm's own decision
    invisible. `append` wrote `PREAMBLE` only when the file did not exist, so a
    queue created on 5 September still said *five resolutions* after a sixth --
    **build the field**, approved by the firm on 7 September -- was added to the
    code. The table an agent reads to decide what to do about a refusal is the
    one on disk, and it was a snapshot of the day the file happened to be made.

    Only the preamble moves. Entries are never touched: they are the record.
    """
    cut = text.find(_FIRST_ENTRY)
    entries = text[cut + 1:] if cut != -1 else ""
    return PREAMBLE + entries


def append(path: Path, entry: Unsupported) -> Path:
    """Add one entry. Creates the file with its preamble if absent.

    Idempotent on id: re-recording the same refusal returns without duplicating
    it, because a queue that grows a new row every retry stops being readable
    and the count stops meaning anything.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(PREAMBLE, encoding="utf-8")
    text = _refreshed(path.read_text(encoding="utf-8"))
    current = parse(text)

    # THE ID IS DECIDED HERE, AGAINST THE QUEUE ON DISK. `from_refusal` numbers
    # from whatever list it was handed, and its default is an empty one -- so the
    # natural `append(path, from_refusal(...))` produced U1 every time, collided
    # with the U1 already written, and returned silently. The second refusal and
    # every one after it was dropped by the idempotency guard, from a queue whose
    # entire purpose is to keep them.
    # IDEMPOTENCY IS CHECKED AGAINST EVERY ENTRY, NOT JUST AN ID CLASH. Written
    # the other way, the SUPPORTED path defeated it: pass the parsed queue as
    # `existing` and the retry gets a fresh id, so the clash search never ran and
    # the same finding was appended twice. Same guarantee, two ways in, and only
    # one of them held it.
    if any(_same_refusal(u, entry) for u in current):
        return path
    if any(u.id == entry.id for u in current):
        entry = replace(entry, id=next_id(current))

    sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    path.write_text(text + sep + entry.render() + "\n---\n\n", encoding="utf-8")
    return path


def _held_citations(desk) -> tuple[str, ...]:
    """Every citation this desk can actually answer from.

    Both stores, because both are authority: a stored passage and a ratified
    position differ in who wrote them, not in whether the desk holds the rule.
    `Desk.authority_for` already treats them alike and this must not disagree
    with it.
    """
    return tuple([p.citation for p in desk.passages]
                 + [q.citation for q in desk.positions if not q.proposed])


def _same_refusal(a: Unsupported, b: Unsupported) -> bool:
    """Idempotency is about the REFUSAL, not the row.

    Compared on what identifies the event -- the question, what was concluded,
    what was cited and why it failed. Not the date, and not the id: re-recording
    the same refusal tomorrow is the same finding, and a queue that grows a row
    per retry stops being readable.
    """
    return ((a.question, a.concluded, a.believed_authority, a.failed_because)
            == (b.question, b.concluded, b.believed_authority, b.failed_because))


def next_id(existing: list[Unsupported]) -> str:
    """Ids are never reused. A gap with no explanation invites being filled."""
    used = {int(m.group(1)) for u in existing
            if (m := re.fullmatch(r"U(\d+)", u.id))}
    return f"U{max(used, default=0) + 1}"


def from_question(question: str, *, why: str = "", model: str = "",
                  because: str = "authority_absent",
                  existing: list[Unsupported] | None = None,
                  today: str | None = None) -> Unsupported:
    """A question nobody has answered yet. The front door for a stuck agent.

    `from_refusal` needs an answer and a grade, because it records a desk that
    TRIED. This records one that could not start: an agent working a close, or a
    person at the desk, holding a question the record has nothing to say about.

    THE QUEUE ALREADY KNOWS WHAT TO DO WITH IT. Its three resolutions are the
    three things a stuck question can turn out to be -- authority that exists and
    was never loaded, a call the rules do not settle, or a thing nobody should be
    asking -- and each is promoted by pull request, never automatically. So a
    stuck agent's questions land where the resolution path already is, rather
    than in a list somebody has to re-read.

    `because` defaults to `authority_absent`, which is the honest reading of "no
    desk holds this": the resolution is to add the authority, cited. Pass
    `facts_not_established` where the rule is clear and what is missing is a fact
    -- what was bought, which entity, which period -- because that resolves by
    ASKING rather than by loading anything.

    NOTHING HERE IS AN ANSWER, and the queue's own rule holds: an entry is never
    returned to a caller and never counted as correct. Retained is not accepted.
    """
    if because not in QUESTION_REASONS:
        raise RecordError(
            f"a question fails for one of {', '.join(QUESTION_REASONS)}, not "
            f"{because!r}. The rest of the engine's reasons describe an answer "
            f"that was tried, and this field is written into the queue "
            f"unescaped because it is a closed vocabulary"
        )
    existing = existing or []
    return Unsupported(
        id=next_id(existing),
        question=question,
        concluded="(nothing offered — this is a question, not an answer)",
        believed_authority="",
        failed_because=because,
        recorded=today or date.today().isoformat(),
        model=model,
        working=why,
    )


def from_refusal(question: str, answer, result, *, model: str = "",
                 existing: list[Unsupported] | None = None,
                 today: str | None = None, desk=None) -> Unsupported:
    """Build the entry the engine keeps when it refuses to serve an answer.

    IT RECORDS WHICH KIND OF REFUSAL THIS IS, WHEN THE DESK IS HANDED IN.
    Measured on the second scoreboard, 4 September 2026: the frontier row cited
    the governing rule in 16 of 16 problems and named the paragraph the
    regulation's own conclusion names in 4 -- so 12 answers reached a finer
    point INSIDE the desk's authority and all 12 were filed here as
    undifferentiated refusals. The queue's whole job is to say what authority is
    missing, and 12 of its 16 entries were not missing authority at all.

    So it asks the question that is answerable at serve time as well as on a
    scoreboard: is there a citation this desk HOLDS that contains the one
    offered? There is no answer key for a client's question; there is always the
    record. The closest containing citation is the one kept -- the nearest
    ancestor says more than the broadest.

    NOTHING ABOUT GRADING OR SERVING CHANGES. The firm declined loosening the
    citation check, and the reason stands: `_check` is shared by `serve()` and
    `grade()` on purpose, so anything that forgives a near miss on a scoreboard
    hands one to a client. This is a label on a retained refusal, not a pass.
    """
    existing = existing or []
    held = ()
    if desk is not None and answer.citation:
        held = tuple(c for c in _held_citations(desk)
                     if record_under(answer.citation, c))
    return Unsupported(
        falls_under=max(held, key=len) if held else "",
        asked=getattr(result, "ask", "") or "",
        # BOTH OR NEITHER. `engine` sets them together on the refusals that name
        # a fact; a half-filled pair would be a field request with no chain.
        needs_field=(getattr(result, "fact", "") or ""
                     if result.reason == "no_field_for_this_fact" else ""),
        asked_by=(getattr(result, "by_position", "") or ""
                  if result.reason == "no_field_for_this_fact" else ""),
        id=next_id(existing),
        question=question,
        concluded=answer.position or "(no position offered)",
        believed_authority=answer.citation,
        failed_because=result.reason or "no_citation",
        recorded=today or date.today().isoformat(),
        model=model,
        working=answer.working,
    )
