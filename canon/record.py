"""The record: convictions and tenets, parsed from and rendered to Markdown.

WHY MARKDOWN AND NOT A DATABASE. The record has to be readable by a person
without a tool, diffable in a pull request, and legible in five years when
whatever wrote it is gone. Its history is the point -- what the firm used to
believe is worth as much as what they believe now -- and `git log` over a
Markdown file is a better history than any schema this could invent.

THE CANONICAL FORM IS ENFORCED, NOT SUGGESTED. `render(parse(text)) == text`
for the committed record, which means a hand edit that breaks the shape is
caught by a test rather than discovered by a parser silently dropping a field.
A record that loses an entry quietly is worse than one that refuses to load.

WHAT IS NEVER ALTERED. The firm's quote and their reason. Retirement adds
lines and flips a state; it does not touch the words. Evidence appends. There
is no operation here that rewrites something the firm said, because a record
that can revise its own quotations is not a record.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONVICTIONS = HERE / "CONVICTIONS.md"
TENETS = HERE / "TENETS.md"

HELD, RETIRED = "held", "retired"


def touches(text: str, term: str) -> bool:
    """Whole words only. THE ONLY MATCHING RULE IN THIS CODEBASE.

    Substring matching made "extension" fire on "extensive", "rate" on
    "generate", and -- in the miner, on its first run -- "refuse" on four
    pasted terminal transcripts saying "refused". A false positive is not a
    cosmetic problem here: it is the thing that teaches somebody to stop
    reading the output.

    It lives in `record.py` rather than in each caller because it was briefly
    written twice, once whole-word and once not, and the two disagreed for a
    day without anything comparing them (S31). One rule, one place.
    """
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.I) is not None


class RecordError(ValueError):
    """The record could not be read as a record. Never silently tolerated."""


@dataclass(frozen=True)
class Conviction:
    """One thing the firm believes, in their own words.

    `fires_on` is what makes candidate selection DETERMINISTIC. The firm asked
    for outcomes that are deterministic wherever possible, and "does this
    decision contradict this belief" is not a question code can answer -- but
    "does this decision touch the subject this belief is about" is. So the
    machine narrows, in a way that can be tested, and the judgement that
    remains is made in the open by whoever is reading.
    """
    id: str
    title: str
    state: str
    recorded: str
    applies: str
    quote: str
    said_by: str
    why: str
    fires_on: tuple[str, ...] = ()
    challenge_note: str = ""
    wrong_note: str = ""
    retired_on: str = ""
    retired_because: str = ""

    @property
    def held(self) -> bool:
        return self.state == HELD


@dataclass(frozen=True)
class Declined:
    """A proposal the firm considered and said no to.

    WHY A REFUSAL IS KEPT AT ALL. Without this, the miner surfaces the same
    passage next month and the same proposal comes back -- and a thing that
    re-asks a question you have already answered is a thing you learn to
    dismiss without reading. The firm asked for something that pushes back only
    when they contradict themselves; re-proposing a declined entry is the exact
    opposite of that.

    It also explains the gaps. Ids are never reused, so a declined proposal
    leaves a hole in the sequence, and a hole with no explanation is an
    invitation to fill it.
    """
    cid: str
    on: str
    source: str
    quote: str
    because: str


@dataclass(frozen=True)
class Evidence:
    project: str
    when: str
    citation: str
    detail: str


@dataclass(frozen=True)
class Tenet:
    id: str
    title: str
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)

    @property
    def bare(self) -> bool:
        """A rule with nothing under it. Visible rather than implied."""
        return not self.evidence


# ── convictions ───────────────────────────────────────────────────────────

_C_HEAD = re.compile(r"^## (C\d+) · (.+)$", re.M)


def _field(block: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*[ ]?(.*?)$", block, re.M)
    return m.group(1).strip() if m else ""


def parse_convictions(text: str) -> list[Conviction]:
    out: list[Conviction] = []
    heads = list(_C_HEAD.finditer(text))
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[head.end():end]

        meta = re.search(r"^\*\*State:\*\* (\w+) · \*\*Recorded:\*\* ([\d-]+) · "
                         r"\*\*Applies:\*\* (.+)$", block, re.M)
        if not meta:
            raise RecordError(f"{head.group(1)} has no state/recorded/applies line")

        # `[^\n]+` FOR THE ATTRIBUTION, NOT `.+`. The quote itself may wrap over
        # several lines, which needs DOTALL -- and DOTALL made the attribution
        # greedy across newlines too, so `said_by` swallowed the rest of the
        # entry: the reason, the triggers, everything. Nothing complained,
        # because a parser that absorbs too much still returns an object.
        # Caught by the round-trip check on its first run, which is what that
        # check is for.
        quote = re.search(r"^> (.+?)\n> — ([^\n]+)$", block, re.M | re.S)
        if not quote:
            raise RecordError(f"{head.group(1)} does not quote the firm")
        said, by = quote.group(1), quote.group(2).strip()
        said = " ".join(l.lstrip("> ").strip() for l in said.splitlines()).strip()

        fires = _field(block, "Fires on")
        out.append(Conviction(
            id=head.group(1), title=head.group(2).strip(),
            state=meta.group(1), recorded=meta.group(2), applies=meta.group(3).strip(),
            quote=said.strip("*"), said_by=by,
            why=_field(block, "Why"),
            fires_on=tuple(t.strip().lower() for t in fires.split(",") if t.strip()),
            challenge_note=_field(block, "A challenge looks like"),
            wrong_note=_field(block, "How it could be wrong"),
            retired_on=_field(block, "Retired"),
            retired_because=_field(block, "Retired because"),
        ))
    if not out:
        raise RecordError("no convictions found; the record is unreadable")
    return out


CONVICTIONS_PREAMBLE = """# Convictions — what the firm believes, and why

**How this file works.** Each entry carries the firm's **own words**, the reason,
the date it was recorded, where it applies, and whether it is `held` or
`retired`.

**Nothing enters without the firm's yes.** Bassy drafts an entry quoting them and
asks. A conviction paraphrased is one they will disown the moment it is read back
at them — and a challenge built on a misquote does not merely fail, it teaches
them to ignore the next one.

**Nothing is ever deleted.** A conviction that stops being true is *retired*: it
gains a date and a reason, stops firing challenges, and stays readable. What the
firm used to believe, and why they stopped, is worth as much as what they believe
now — and it means nothing already settled gets re-litigated a year later.

**The challenge is the review.** There is no renewal queue and no annual audit.
A conviction is examined at the moment it bites, which is the only moment anyone
has the context to judge it.

**`Fires on`** is what makes selection deterministic: the subjects that bring a
conviction into play. Code narrows to candidates; the judgement of whether a
candidate is really a contradiction is made in the open, by a person reading.
"""


_D_HEAD = re.compile(r"^### (C\d+) · declined ([\d-]+) · (.+)$", re.M)

DECLINED_PREAMBLE = """## Not convictions

Proposals the firm read and said no to. They are kept for two reasons. The
miner surfaces the same passages every time it runs, and a thing that re-asks a
question you have already answered is a thing you learn to dismiss without
reading. And ids are never reused, so a declined proposal leaves a gap in the
sequence — a gap with no explanation is an invitation to fill it.
"""


def parse_declined(text: str) -> list[Declined]:
    out: list[Declined] = []
    heads = list(_D_HEAD.finditer(text))
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[head.end():end]
        quote = re.search(r"^> (.+?)$", block, re.M)
        if not quote:
            raise RecordError(f"{head.group(1)} was declined without a quotation")
        out.append(Declined(cid=head.group(1), on=head.group(2),
                            source=head.group(3).strip(),
                            quote=quote.group(1).strip().strip("*"),
                            because=_field(block, "Not a conviction because")))
    return out


def render_convictions(items: list[Conviction],
                       declined: list[Declined] | None = None,
                       preamble: str = CONVICTIONS_PREAMBLE) -> str:
    parts = [preamble.rstrip() + "\n"]
    for c in items:
        parts.append("\n---\n")
        parts.append(f"\n## {c.id} · {c.title}\n\n")
        parts.append(f"**State:** {c.state} · **Recorded:** {c.recorded} · "
                     f"**Applies:** {c.applies}\n\n")
        parts.append(f"> *{c.quote}*\n> — {c.said_by}\n\n")
        parts.append(f"**Why:** {c.why}\n\n")
        parts.append(f"**Fires on:** {', '.join(c.fires_on)}\n")
        if c.challenge_note:
            parts.append(f"\n**A challenge looks like:** {c.challenge_note}\n")
        if c.wrong_note:
            parts.append(f"\n**How it could be wrong:** {c.wrong_note}\n")
        if c.state == RETIRED:
            parts.append(f"\n**Retired:** {c.retired_on}\n")
            parts.append(f"\n**Retired because:** {c.retired_because}\n")
    for i, d in enumerate(declined or ()):
        if i == 0:
            parts.append("\n---\n\n" + DECLINED_PREAMBLE)
        parts.append(f"\n### {d.cid} · declined {d.on} · {d.source}\n\n")
        parts.append(f"> *{d.quote}*\n\n")
        parts.append(f"**Not a conviction because:** {d.because}\n")
    return "".join(parts)


# ── the two operations that change a conviction ───────────────────────────

def add(items: list[Conviction], new: Conviction, *, confirmed: bool) -> list[Conviction]:
    """Append a conviction. REFUSES WITHOUT AN EXPLICIT YES.

    The confirmation is a required argument rather than a convention, because
    a convention is something a caller written next year will not know about.
    Nothing can add to this record by accident.
    """
    if not confirmed:
        raise RecordError(
            f"{new.id} was not confirmed by the firm, so it is not recorded. "
            f"A conviction they did not agree to is one they will disown the "
            f"moment it is quoted back at them.")
    if any(c.id == new.id for c in items):
        raise RecordError(f"{new.id} already exists; ids are not reused")
    if not new.quote.strip():
        raise RecordError(f"{new.id} carries no quotation. A conviction in "
                          f"somebody else's words is not the firm's conviction.")
    return [*items, new]


def retire(items: list[Conviction], cid: str, *, because: str,
           on: str | None = None) -> list[Conviction]:
    """Retire a conviction: it stops firing, and it stays.

    THE WORDS ARE NOT TOUCHED. Only the state, and two added lines. What the
    firm used to believe is the record's most useful property -- it is what
    stops something already settled being argued again a year later.
    """
    if not because.strip():
        raise RecordError(
            f"retiring {cid} needs a reason. A belief that vanished without one "
            f"is indistinguishable from a belief nobody wrote down.")
    out, found = [], False
    for c in items:
        if c.id != cid:
            out.append(c)
            continue
        if c.state == RETIRED:
            raise RecordError(f"{cid} is already retired")
        found = True
        out.append(replace(c, state=RETIRED,
                           retired_on=on or date.today().isoformat(),
                           retired_because=because.strip()))
    if not found:
        raise RecordError(f"{cid} is not in the record")
    return out


# ── tenets ────────────────────────────────────────────────────────────────

_T_HEAD = re.compile(r"^## (S\d+) · (.+)$", re.M)
_E_HEAD = re.compile(r"^### (.+?) · ([\d-]+) · (.+)$", re.M)


def parse_tenets(text: str) -> list[Tenet]:
    out: list[Tenet] = []
    heads = list(_T_HEAD.finditer(text))
    for i, head in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        block = text[head.end():end]
        ev = []
        marks = list(_E_HEAD.finditer(block))
        for j, m in enumerate(marks):
            stop = marks[j + 1].start() if j + 1 < len(marks) else len(block)
            # THE SEPARATOR BELONGS TO THE FORMAT, NOT THE EVIDENCE. An
            # entry's detail runs to the next heading, which means it swallows
            # the `---` that divides tenets -- and the renderer then writes a
            # second one beside it, growing the file by one separator per
            # tenet on every write. Trimmed here, at the boundary where the
            # format is understood, rather than by every caller.
            detail = block[m.end():stop].strip()
            if detail.endswith("---"):
                detail = detail[:-3].rstrip()
            ev.append(Evidence(project=m.group(1).strip(), when=m.group(2),
                               citation=m.group(3).strip(), detail=detail))
        out.append(Tenet(id=head.group(1), title=head.group(2).strip(),
                         evidence=tuple(ev)))
    return out


TENETS_PREAMBLE = """# Tenets — how to build

**How this file works.** Each tenet is a rule, then the incidents that proved
it. Evidence **appends**; it is never rewritten. Every entry names the project,
the date, and a citation you can go and read — a commit, a quotation, a comment,
or a test docstring.

**A rule with nothing under it does not belong in this file.** The test each one
had to pass: *if this rule had been in force, would that bug have shipped?*

Identifiers match `SATC/docs/SOFTWARE-TENETS.md` — `S31` here is `S31` there —
so every citation already written across that repository still resolves.

**Evidence count is reported, not implied.** A tenet carrying one incident is a
local observation. One carrying three, from three projects, is a law. The
difference should be visible without reading.

**Ratified by the firm, 3 September 2026**, after reading them: *"i was reviewing
the tenets - i am agreed with them."* That date matters. Before it these were
thirty-five observations an agent had written down about its own mistakes; after
it they are the firm's rules, and a build that breaks one is answerable to them
rather than to a document.
"""


def render_tenets(items: list[Tenet], preamble: str = TENETS_PREAMBLE) -> str:
    parts = [preamble.rstrip() + "\n"]
    for t in items:
        by: dict[str, int] = {}
        for e in t.evidence:
            by[e.project] = by.get(e.project, 0) + 1
        tally = ", ".join(f"{p} ×{n}" for p, n in sorted(by.items()))
        parts.append("\n---\n")
        parts.append(f"\n## {t.id} · {t.title}\n\n")
        parts.append(f"**Evidence: {len(t.evidence)}**"
                     + (f" *({tally})*\n" if tally else "\n"))
        for e in t.evidence:
            parts.append(f"\n### {e.project} · {e.when} · {e.citation}\n\n")
            parts.append(e.detail.rstrip() + "\n")
    return "".join(parts)


def add_evidence(items: list[Tenet], tid: str, new: Evidence) -> list[Tenet]:
    """Append evidence. NEVER REWRITES what is already there.

    This is what makes the record compound rather than merely persist: the
    third time a rule bites in a third codebase it carries three citations,
    and at that point it is visibly a law rather than a local quirk.
    """
    out, found = [], False
    for t in items:
        if t.id != tid:
            out.append(t)
            continue
        found = True
        out.append(replace(t, evidence=(*t.evidence, new)))
    if not found:
        raise RecordError(f"{tid} is not in the record")
    return out


def load() -> tuple[list[Conviction], list[Tenet]]:
    return (parse_convictions(CONVICTIONS.read_text(encoding="utf-8")),
            parse_tenets(TENETS.read_text(encoding="utf-8")))
