"""Mining the corpus: surface what the firm said, propose, never write.

WHAT THIS IS FOR. Two files hold everything the firm typed between 21 August
and 3 September 2026 -- 173 turns and 44 interview answers, pulled out of the
session transcripts before the container holding them was wiped. The
convictions are in there. Nobody has read them back.

THE LINE THIS FILE DOES NOT CROSS. Mining does not decide what a conviction
is. It narrows a corpus to passages, and a person reads them. The difference
matters because the alternative -- code that reads seven thousand words and
announces what somebody believes -- is the confident wrong answer this
operation has been bitten by twice in a week, except now it would be wrong
about the firm's own convictions, in their name, in a file they will be
challenged from later.

TWO TIERS, REPORTED SEPARATELY, because one is deterministic and one is not.

  TYPED answers are surfaced unconditionally. An interview offered options and
  the firm rejected the framing and wrote their own -- that rejection is the
  signal, and detecting it needs no judgement at all. Seventeen of forty-four.

  TURNS are narrowed by marker words, which IS a guess. So they are counted
  and labelled as a guess, never blended into the same list. A tool that
  presents its guesses and its certainties in one undifferentiated column has
  taught you to distrust both.

THE QUOTE IS CHECKED AGAINST THE CORPUS, not trusted. `Proposal` refuses to
exist if its quote is not literally present in the passage it claims to come
from. Paraphrase is the failure that burns the whole mechanism -- a conviction
in somebody else's words is one the firm disowns the moment it is read back at
them -- so it is made impossible here rather than warned about.

NOTHING HERE WRITES. `commit` hands the proposal to `record.add`, which refuses
without an explicit yes. There is no other path out of this module, and
`test_mining_cannot_reach_the_record_except_through_the_confirmation` holds it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from record import (Conviction, Declined, RecordError, add,
                    render_convictions, touches)

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus"
TURNS_FILE = CORPUS / "the-firms-own-words.md"
DECISIONS_FILE = CORPUS / "decisions-in-their-words.md"

# A turn that is an attached screenshot and nothing else. It carries no words,
# so it cannot carry a conviction -- but it is COUNTED rather than dropped,
# because a denominator that quietly excludes what it could not read is the
# denominator that makes a green check meaningless (S2).
_IMAGE_ONLY = re.compile(r"^\[Image: [^\]]*\]$")

_HEAD = re.compile(r"^### ([\d]{4}-[\d]{2}-[\d]{2}) ([\d:]{8})(  · TYPED)?$", re.M)

# THE MARKER LIST IS SHORT ON PURPOSE, and every word on it is a word somebody
# uses about what they want rather than about what they are doing. It is a
# guess; it is labelled as one everywhere it appears. Growing it until it
# matches everything would not make it better, it would make the guess
# invisible.
MARKERS: tuple[str, ...] = (
    "never", "always", "i want", "i don't want", "i dont want",
    "should never", "must", "i just don't think", "i just dont think",
    "not right", "i would never", "i will not", "won't", "refuse",
    "i believe", "i care", "on purpose", "deliberately", "the rule",
)


@dataclass(frozen=True)
class Passage:
    """One thing the firm typed, with where and when it was typed."""
    source: str
    when: str
    text: str
    typed: bool = False
    asked: str = ""

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True)
class Survey:
    """The denominator. What was examined, and what could not be.

    Reported on every run whether or not anything was found, because a mining
    run that surfaces nothing and says nothing is indistinguishable from one
    that never opened the files.
    """
    turns: int
    turns_without_words: int
    decisions: int
    typed: int
    words: int
    first: str
    last: str

    @property
    def read(self) -> int:
        return self.turns - self.turns_without_words + self.decisions

    def say(self) -> str:
        return (f"{self.turns} turn(s) and {self.decisions} interview answer(s) "
                f"examined, {self.first} to {self.last}\n"
                f"  {self.read} carried words; {self.turns_without_words} were "
                f"screenshots with no text\n"
                f"  {self.typed} answer(s) were typed rather than picked\n"
                f"  {self.words:,} words read")


def _blocks(text: str, source: str) -> list[tuple[str, bool, str]]:
    """(body, typed, timestamp) for each `### date time` heading."""
    out = []
    heads = list(_HEAD.finditer(text))
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append((text[h.end():end].strip(), bool(h.group(3)),
                    f"{h.group(1)} {h.group(2)}"))
    return out


def read_turns(text: str) -> list[Passage]:
    """Every turn, screenshots included. Excluding them here would hide them
    from the count, and the count is the point."""
    return [Passage(source=TURNS_FILE.name, when=when, text=body)
            for body, _typed, when in _blocks(text, TURNS_FILE.name)]


def read_decisions(text: str) -> list[Passage]:
    """Interview answers. The chosen text is the firm's; the question is not."""
    out = []
    for body, typed, when in _blocks(text, DECISIONS_FILE.name):
        asked = re.search(r"^\*\*Asked:\*\* (.+?)(?=\n\n|\Z)", body, re.M | re.S)
        chose = re.search(r"^\*\*Chose:\*\* (.+?)(?=\n\n|\Z)", body, re.M | re.S)
        if not chose:
            continue
        out.append(Passage(source=DECISIONS_FILE.name, when=when,
                           text=" ".join(chose.group(1).split()), typed=typed,
                           asked=" ".join(asked.group(1).split()) if asked else ""))
    return out


def survey(turns: list[Passage], decisions: list[Passage]) -> Survey:
    blank = sum(1 for p in turns if not p.text or _IMAGE_ONLY.match(p.text))
    every = [p for p in turns + decisions]
    stamps = sorted(p.when for p in every) or ["—", "—"]
    return Survey(
        turns=len(turns), turns_without_words=blank, decisions=len(decisions),
        typed=sum(1 for p in decisions if p.typed),
        words=sum(p.words for p in every if not _IMAGE_ONLY.match(p.text)),
        first=stamps[0][:10], last=stamps[-1][:10])


def markers_in(text: str) -> tuple[str, ...]:
    """Whole words, through the one matching rule.

    This was `m in low` on its first run and "refuse" matched "refused" in four
    pasted terminal transcripts -- four of the noisiest hits in a list whose
    only job is to be worth reading.
    """
    return tuple(m for m in MARKERS if touches(text, m))


def around(text: str, term: str, width: int = 150) -> str:
    """The words either side of the hit, not the first line of the turn.

    The first line of a turn is often "ok so" or "NOW" -- true, useless, and
    it made three real passages look like noise on the first run. Show the
    reader the part that caused the hit, so they can dismiss it in one glance
    rather than opening the corpus.
    """
    flat = " ".join(text.split())
    m = re.search(rf"(?<!\w){re.escape(term)}(?!\w)", flat, re.I)
    if not m:
        return flat[:width]
    start = max(0, m.start() - width // 3)
    end = min(len(flat), m.end() + (width - width // 3))
    return ("…" if start else "") + flat[start:end] + ("…" if end < len(flat) else "")


def surfaced(turns: list[Passage], decisions: list[Passage]
             ) -> tuple[list[Passage], list[tuple[Passage, tuple[str, ...]]]]:
    """Two lists, never one. Certain first, guessed second.

    Returns (typed answers, [(turn, the markers that surfaced it)]). The caller
    prints them under separate headings; merging them is the thing this shape
    exists to prevent.
    """
    certain = [p for p in decisions if p.typed]
    guessed = []
    for p in turns:
        if not p.text or _IMAGE_ONLY.match(p.text):
            continue
        hit = markers_in(p.text)
        if hit:
            guessed.append((p, hit))
    return certain, guessed


def already_declined(declined: list[Declined], passage: Passage) -> str:
    """The id of a proposal the firm already said no to from this passage.

    A RECORD OF REFUSALS THAT NOTHING READS IS A DOCUMENT, NOT A GUARD. This is
    the half that makes keeping them worth anything: the miner surfaces the same
    passages every run, and without this the same declined proposal comes back
    every month until somebody stops reading the output entirely.
    """
    for d in declined:
        if d.quote and d.quote in passage.text:
            return d.cid
    return ""


def already_said(convictions: list[Conviction], passage: Passage) -> list[str]:
    """Which convictions already on the record this passage touches.

    Not a filter. A passage that touches C1 may still be worth recording -- it
    may be the reason BEHIND C1, or the first sign C1 is being contradicted.
    It is flagged so whoever reads it knows, not hidden so nobody does.
    """
    return [c.id for c in convictions
            if any(touches(passage.text, t) for t in c.fires_on)]


@dataclass(frozen=True)
class Proposal:
    """A drafted conviction, and the passage it is drawn from. NOT RECORDED.

    Construction refuses anything that could not be defended when the firm
    reads it back: a quote absent from the passage, a missing reason, a
    missing date. Each of those has to be impossible rather than discouraged,
    because the person who would have caught it is the person the proposal is
    being shown to, and by then the misquote has already been read.
    """
    draft: Conviction
    passage: Passage

    def __post_init__(self) -> None:
        if not self.draft.quote.strip():
            raise RecordError("a proposal with no quotation is a paraphrase "
                              "with extra steps")
        if self.draft.quote.strip() not in self.passage.text:
            raise RecordError(
                f"{self.draft.id}: the quote is not in the passage it claims. "
                f"A conviction in somebody else's words is one the firm will "
                f"disown the moment it is read back at them.")
        if not self.draft.why.strip():
            raise RecordError(f"{self.draft.id}: no reason. The reason is what "
                              f"gets re-examined later; without it there is "
                              f"nothing to ask about.")
        if not self.draft.recorded.strip():
            raise RecordError(f"{self.draft.id}: no date. A conviction with no "
                              f"date cannot be told from a current one.")

    def ask(self) -> str:
        """The exact text that would be stored, then the question.

        IT IS RENDERED BY THE RENDERER, not retyped beside it. This was a
        hand-built list of labelled lines -- a second description of the same
        entry, in a second place, with nothing comparing them (S31). It had
        already drifted in one visible way: a quote containing quotation marks
        came out as `"…a "loss""`, because the display wrapped what the file
        does not. Showing the firm a rendering that is not the file is exactly
        the misquote this whole mechanism is built to avoid.
        """
        where = f"{self.passage.source} · {self.passage.when}"
        asked = f"\nYou were asked: {self.passage.asked}\n" if self.passage.asked else ""
        stored = render_convictions([self.draft], preamble="").strip()
        return (f"From {where}"
                f"{' (you typed this rather than picking)' if self.passage.typed else ''}\n"
                f"{asked}\n"
                f"This is exactly what would be written to the record:\n\n"
                + "\n".join(f"  {line}" if line else "" for line in stored.splitlines())
                # THE RULE IS NOT DECORATION. A rendered entry ends with a field,
                # and a field's value runs until the next field or a rule -- so
                # prose appended straight after it is, structurally, part of that
                # field. Without this the closing question below parsed back as
                # the tail of `How it could be wrong`. It also does the thing it
                # looks like it does: shows the firm where the entry stops.
                + "\n\n  ---"
                + "\n\nIs that right, in your words? "
                  "Nothing is written until you say so.")


def commit(items: list[Conviction], proposal: Proposal, *,
           confirmed: bool) -> list[Conviction]:
    """The ONLY way out of this module. Goes through the confirmation.

    Deliberately a one-line pass-through rather than its own implementation:
    a second write path is a second place for the confirmation to be forgotten,
    and it would be forgotten in the one that nobody was looking at.
    """
    return add(items, proposal.draft, confirmed=confirmed)


def load_corpus() -> tuple[list[Passage], list[Passage]]:
    return (read_turns(TURNS_FILE.read_text(encoding="utf-8")),
            read_decisions(DECISIONS_FILE.read_text(encoding="utf-8")))


def report(certain: list[Passage],
           guessed: list[tuple[Passage, tuple[str, ...]]],
           s: Survey, convictions: list[Conviction],
           declined: list[Declined] | None = None) -> str:
    declined = declined or []
    lines = [s.say(), ""]
    lines.append(f"— {len(certain)} answer(s) you typed rather than picked. "
                 f"Rejecting the framing is the signal; no judgement in this list.")
    for p in certain:
        no = already_declined(declined, p)
        if no:
            # SAID ONCE, QUIETLY, AND NOT PROPOSED AGAIN. The passage stays
            # visible so the count still adds up; what is gone is the proposal.
            lines.append(f"\n  {p.when}  [you declined this as {no}]  {p.text}")
            continue
        seen = already_said(convictions, p)
        note = f"   (touches {', '.join(seen)} already on the record)" if seen else ""
        lines.append(f"\n  {p.when}  {p.text}{note}")
    lines.append(f"\n\n— {len(guessed)} turn(s) surfaced by a marker word. "
                 f"THIS HALF IS A GUESS about relevance, and is listed apart "
                 f"from the half that is not.")
    for p, hit in guessed:
        no = already_declined(declined, p)
        mark = f"you declined this as {no}" if no else ", ".join(hit)
        lines.append(f"\n  {p.when}  [{mark}]\n"
                     f"    {around(p.text, hit[0])}")
    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover - the operator's entry point
    from record import CONVICTIONS, load, parse_declined

    convictions, _ = load()
    declined = parse_declined(CONVICTIONS.read_text(encoding="utf-8"))
    turns, decisions = load_corpus()
    s = survey(turns, decisions)
    certain, guessed = surfaced(turns, decisions)
    print(report(certain, guessed, s, convictions, declined))
    print("\nNothing above is recorded. Each one is a proposal until you say yes.")
