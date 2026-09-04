"""The record a desk answers from: its sources, its problems, its authority.

WHY MARKDOWN AND NOT YAML. The PRD draws these files as YAML. They are Markdown,
and the reason is a constraint rather than a preference: this plugin installs with
`pip install pytest` and nothing else, because canon proved that a plugin which
lifts out whole is worth more than one with conveniences. Python has no YAML in
its standard library, so YAML would mean a dependency. Canon already parses
exactly this shape -- `## ID · Title`, `**Field:** value`, `> quote` -- so the
choice is between reusing a format that works and adding a parser beside it.

The second reason is the one that matters more. **The pull request is the firm's
yes.** A record they ratify by reading a diff should read like prose in that diff,
and a forty-five entry extraction is more legible as Markdown than as YAML.

WHAT IS DETERMINISTIC HERE. Everything. This module reads files and returns
frozen dataclasses; it makes no judgement, contacts no network, and holds no
opinion about whether an answer is right. A malformed entry RAISES rather than
defaulting, for the reason canon's own record gives: a parser that quietly
absorbs a bad block still returns an object, and nothing downstream can tell the
difference between a field that was empty and a field that was never read.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class RecordError(Exception):
    """The record could not be read as a record. Never silently tolerated."""


# ── the vocabulary, kept in one place so a typo is a failure and not a branch ──

TIERS = ("primary", "secondary", "tertiary")

#: How a source is reached. Declared on the source, never discovered by failing:
#: if a failed fetch were what reached for a heavier client, then a site refusing
#: automated access would be the thing that triggered one.
ACCESS = ("public_fetch", "headless_browser", "signed_in_browser", "human_only")

#: What may be copied into this repository from a source. `license_check` is the
#: default and it stores nothing -- a licence the firm holds may permit an
#: internal copy, which is why this is a fact about each source rather than one
#: policy over all of them.
MAY_STORE = ("full_text", "citation_only", "license_check")

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class Source:
    """One body of authority a desk is allowed to rely on."""
    id: str
    title: str
    tier: str
    access: str
    may_store: str
    checked: str
    citation_prefix: str
    url: str = ""
    note: str = ""

    @property
    def binding(self) -> bool:
        """Only primary authority can settle a question on its own.

        Secondary and tertiary are somebody's reading of the rule. An answer
        resting only on those is the case where authority permits a choice, and
        a choice belongs to the firm -- so it escalates rather than answers.
        """
        return self.tier == "primary"

    @property
    def readable(self) -> bool:
        """Whether the engine may fetch this source at all.

        `human_only` is not a stricter fetch, it is the absence of one. FASB ASC
        is the worked example: its licence forbids the content reaching a model
        by any route, so no client rescues it and the engine never reaches.
        """
        return self.access != "human_only"


@dataclass(frozen=True)
class Passage:
    """One piece of authority text, stored because its source permits it."""
    citation: str
    source_id: str
    checked: str
    text: str


@dataclass(frozen=True)
class Problem:
    """A fact pattern whose answer is already known, used to score a desk.

    The answer is not ours. Every problem here is a worked example from public
    authority, which is what makes the denominator meaningful: a score against
    answers we wrote ourselves measures agreement, not correctness.
    """
    id: str
    title: str
    citation: str
    answer: str
    facts: str


@dataclass(frozen=True)
class Desk:
    """One expert: what it answers on, what it may rely on, how it is scored.

    `positions` is not decoration. For a source the engine may never read --
    FASB ASC, whose licence forbids the content reaching a model at all -- a
    ratified position is the desk's ENTIRE knowledge of it. Loading only
    `passages` made every such citation refuse as `authority_absent`, which
    left the advertised position path unusable.
    """
    name: str
    sources: tuple[Source, ...] = field(default_factory=tuple)
    passages: tuple[Passage, ...] = field(default_factory=tuple)
    problems: tuple[Problem, ...] = field(default_factory=tuple)
    positions: tuple = field(default_factory=tuple)

    def source(self, source_id: str) -> Source | None:
        return next((s for s in self.sources if s.id == source_id), None)

    def passage(self, citation: str) -> Passage | None:
        """Look up authority by its citation. Exact match, deliberately.

        A fuzzy lookup here would let an answer cite something adjacent to the
        rule it relied on and still verify, which is the failure the whole
        citation check exists to catch.
        """
        return next((p for p in self.passages if p.citation == citation), None)

    def position(self, citation: str):
        """A ratified position resting on this citation, if the firm took one.

        Only ratified ones answer. A proposal sitting in a pull request is not
        yet the firm's word, and serving it would be recording an answer they
        never gave.
        """
        return next((p for p in self.positions
                     if p.citation == citation and not p.proposed), None)

    def authority_for(self, citation: str):
        """Whatever backs this citation: stored text, or the firm's own words.

        Returns `(kind, obj, source)` or None. Both are real authority; they
        differ in who wrote them, which is why they are stored apart.
        """
        if (p := self.passage(citation)) is not None:
            return "passage", p, self.source(p.source_id)
        if (pos := self.position(citation)) is not None:
            src = next((s for s in self.sources
                        if citation.startswith(s.citation_prefix)), None)
            return "position", pos, src
        return None


# ── parsing ───────────────────────────────────────────────────────────────────

_HEAD = re.compile(r"^## (\S+) · (.+)$", re.M)
_BARE_HEAD = re.compile(r"^## (.+)$", re.M)


def _blocks(text: str, pattern: re.Pattern) -> list[tuple[re.Match, str]]:
    heads = list(pattern.finditer(text))
    return [
        (h, text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)])
        for i, h in enumerate(heads)
    ]


def _field(block: str, label: str, where: str, *, required: bool = True) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*[ ]?(.*?)$", block, re.M)
    if m and m.group(1).strip():
        return m.group(1).strip()
    if required:
        raise RecordError(f"{where}: no '{label}' field")
    return ""


def _inline(block: str, label: str, where: str) -> str:
    """A field sharing a line with others, separated by ' · '."""
    m = re.search(rf"\*\*{re.escape(label)}:\*\*[ ]?([^·\n]+)", block)
    if not m or not m.group(1).strip():
        raise RecordError(f"{where}: no '{label}' field")
    return m.group(1).strip()


def _one_of(value: str, allowed: tuple[str, ...], label: str, where: str) -> str:
    if value not in allowed:
        raise RecordError(
            f"{where}: {label} is {value!r}; must be one of {', '.join(allowed)}"
        )
    return value


def _date(value: str, label: str, where: str) -> str:
    if not _DATE.match(value):
        raise RecordError(f"{where}: {label} is {value!r}; must be YYYY-MM-DD")
    return value


def parse_sources(text: str) -> list[Source]:
    out = []
    for head, block in _blocks(text, _HEAD):
        sid, title = head.group(1), head.group(2).strip()
        where = f"source {sid}"
        out.append(Source(
            id=sid,
            title=title,
            tier=_one_of(_inline(block, "Tier", where), TIERS, "tier", where),
            access=_one_of(_inline(block, "Access", where), ACCESS, "access", where),
            may_store=_one_of(
                _inline(block, "May store", where), MAY_STORE, "may_store", where),
            checked=_date(_inline(block, "Checked", where), "checked", where),
            citation_prefix=_field(block, "Citation prefix", where),
            url=_field(block, "Url", where, required=False),
            note=_field(block, "Why", where, required=False),
        ))
    if not out:
        raise RecordError("no sources found; a desk with no authority cannot answer")
    return out


def parse_problems(text: str) -> list[Problem]:
    out = []
    for head, block in _blocks(text, _HEAD):
        pid, title = head.group(1), head.group(2).strip()
        where = f"problem {pid}"
        out.append(Problem(
            id=pid,
            title=title,
            citation=_field(block, "Citation", where),
            answer=_field(block, "Answer", where),
            facts=_field(block, "Facts", where),
        ))
    if not out:
        raise RecordError("no problems found; a desk that cannot be scored is a claim")
    return out


def parse_passages(text: str) -> list[Passage]:
    out = []
    for head, block in _blocks(text, _BARE_HEAD):
        citation = head.group(1).strip()
        where = f"passage {citation!r}"
        quote = re.search(r"^> (.+?)(?=\n\n|\n##|\Z)", block, re.M | re.S)
        if not quote:
            raise RecordError(f"{where}: no quoted authority text")
        text_ = " ".join(
            l.lstrip("> ").strip() for l in quote.group(1).splitlines()
        ).strip()
        out.append(Passage(
            citation=citation,
            source_id=_inline(block, "Source", where),
            checked=_date(_inline(block, "Checked", where), "checked", where),
            text=text_,
        ))
    return out


def load(desk_dir: Path) -> Desk:
    """Read one desk off disk. Raises rather than returning a half-read desk."""
    desk_dir = Path(desk_dir)
    if not desk_dir.is_dir():
        raise RecordError(f"no desk at {desk_dir}")

    sources = parse_sources(_read(desk_dir / "SOURCES.md"))
    problems = parse_problems(_read(desk_dir / "PROBLEMS.md"))

    passages: list[Passage] = []
    extracted = desk_dir / "extracted"
    if extracted.is_dir():
        for f in sorted(extracted.glob("*.md")):
            passages.extend(parse_passages(f.read_text(encoding="utf-8")))

    import positions as _positions          # local: positions imports record
    pos: list = []
    pdir = desk_dir / "positions"
    if pdir.is_dir():
        for f in sorted(pdir.glob("*.md")):
            pos.extend(_positions.parse(f.read_text(encoding="utf-8")))

    known = {s.id for s in sources}
    for p in passages:
        if p.source_id not in known:
            raise RecordError(
                f"passage {p.citation!r} cites source {p.source_id!r}, which is not "
                f"in SOURCES.md; authority with no recorded source is unverifiable"
            )

    return Desk(
        name=desk_dir.name,
        sources=tuple(sources),
        passages=tuple(passages),
        problems=tuple(problems),
        positions=tuple(pos),
    )


def _read(path: Path) -> str:
    if not path.is_file():
        raise RecordError(f"no {path.name} at {path.parent}")
    return path.read_text(encoding="utf-8")
