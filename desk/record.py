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
from datetime import date as _date_cls
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


def under(path: str, ancestor: str) -> bool:
    """Whether `path` lies strictly beneath `ancestor`. THE ONLY CONTAINMENT
    RULE IN THIS PLUGIN.

    It lives here rather than in whichever tool needed it first because it was
    briefly written once, in `tools/extract_ecfr.py`, comparing only the
    parenthesised labels and ignoring everything before them. Inside one section
    that is right and a mutation confirmed it. Outside one it is not: the labels
    of `26 CFR 1.263(a)-3(j)(1)` and `26 CFR 1.999(a)-3(j)(1)` are identical, so
    a citation from an unrelated section read as contained. A desk holding two
    sources is all it takes, and the queue below asks this question about
    arbitrary citations a model produced.

    Compared as a prefix ending at a label boundary, which is exact on citations
    written with their parentheses and carries no cross-section hole: `(j)(10)`
    begins with the characters of `(j)(1)`, and the remainder `0)` does not open
    a label, so it is correctly not beneath it.
    """
    if not path or not ancestor or path == ancestor:
        return False
    return path.startswith(ancestor) and path[len(ancestor):].startswith("(")


def from_source(citation: str, prefix: str) -> bool:
    """Whether `citation` comes from the source whose citations begin `prefix`.

    A SECOND BOUNDARY RULE, AND IT IS NOT `under`. `under` asks whether one
    paragraph sits inside another and so demands the remainder open a label with
    `(`. A source prefix is answered against whole citations that continue in
    other ways -- `IRS Pub. 583 (12/2024), "Reconciling the checking account"`
    continues with a comma, and a citation may BE the prefix exactly. So the rule
    is the weaker one that is still exact: the prefix must end where the citation
    stops being the same identifier.

    WHY IT IS NOT `startswith`. It was a bare `startswith` in three places, and
    `meals-and-entertainment` holds both `26 CFR 1.274-5` and its temporary
    counterpart `26 CFR 1.274-5T` -- an ordinary pairing, since the permanent
    section reserves whole paragraphs to the temporary one. Under `startswith`
    every `-5T` citation belongs to BOTH sources.

    SAID EXACTLY, BECAUSE THE SHAPE MATTERS MORE THAN THE SCARE. Only two paths
    resolve a citation by prefix, and both are position paths: `load()`'s
    uniqueness check and `authority_for`'s lookup. A stored PASSAGE carries its
    `source_id` and never asks. So today the desk loads either way -- none of its
    four positions happens to cite the reserved pair -- and the collision is one
    ratified position away, at which point `load()` refuses a desk that is
    correct. The session that hit it while building worked around it in the
    record, ending two prefixes at an open parenthesis; that holds only while
    every citation on that desk names a paragraph, and a rule six records each
    have to remember is not a rule.

    `1.274-1` against `1.274-11` is the same collision with no letter involved,
    and `1.446` against `1.4461` with no punctuation. All three are boundaries.
    """
    if not citation or not prefix or not citation.startswith(prefix):
        return False
    rest = citation[len(prefix):]
    return not rest or not rest[0].isalnum()


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
class Registration:
    """One desk, the subjects that bring it into play, and who answers them."""
    desk: str
    title: str
    fires_on: tuple[str, ...]
    #: `{source_id: subjects}` — WHICH SOURCE ANSWERS WHICH SUBJECT, declared by
    #: the firm rather than inferred by anybody. `fires_on` is its union, so the
    #: two cannot drift: there is no second list to forget to update.
    answered_from: dict = field(default_factory=dict)


def parse_subjects(text: str, desk_name: str) -> Registration:
    blocks = _blocks(text, _SUBJ_HEAD)
    if not blocks:
        raise RecordError(f"{desk_name}: SUBJECTS.md declares no desk")
    head, block = blocks[0]
    # NOT `.*?$`. Canon's own field reader takes a single line, which is right
    # there because its fields are short -- but this list is long enough to wrap,
    # and a single-line read of a wrapped value truncates it SILENTLY. Written
    # that way first, this parsed 5 subjects out of 30 and reported success.
    #
    # `Answered from <id>` AND NOT A BARE `Fires on`, and the difference is the
    # whole of #266. A desk recorded its sources and its subjects and nothing
    # said which source answers which -- so when qwen3:8b answered four
    # bank-reconciliation questions by citing a CFR paragraph about accounting
    # records, nothing exact could refuse it, and `serve()` handed all four out
    # stamped `tier='primary'`. Word overlap was measured in its place and either
    # refused a quarter of the working desk's own correct answers or missed the
    # case entirely. This is the fact recorded instead of guessed at.
    declared = re.findall(
        r"^\*\*Answered from (\S+):\*\*[ ]?(.*?)(?=\n\n|\n\*\*|\Z)",
        block, re.M | re.S)
    if not declared:
        raise RecordError(
            f"{desk_name}: no 'Answered from <source id>' lines. A desk nothing "
            f"routes to is a desk nobody asks -- and a subject with no source "
            f"named is one no citation can be checked against."
        )

    answered_from, order = {}, []
    for source_id, listed in declared:
        terms = tuple(t.strip().lower()
                      for t in " ".join(listed.split()).split(",") if t.strip())
        if not terms:
            raise RecordError(
                f"{desk_name}: 'Answered from {source_id}' names no subjects")
        if source_id in answered_from:
            raise RecordError(
                f"{desk_name}: 'Answered from {source_id}' appears twice; which "
                f"list wins would be decided by file order")
        answered_from[source_id] = terms
        order.extend(t for t in terms if t not in order)
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
        fires_on=tuple(order),
        answered_from=answered_from,
    )



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
    #: The subjects that bring this desk into play, from SUBJECTS.md. Held here
    #: because `engine._check` needs to ask what a QUESTION is about before it
    #: can judge whether a citation has anything to do with it. Empty when the
    #: desk declares none, and the engine then says it could not check rather
    #: than passing the answer as verified.
    fires_on: tuple[str, ...] = field(default_factory=tuple)
    #: `{source_id: subjects}` from SUBJECTS.md — see `Registration`.
    answered_from: dict = field(default_factory=dict)
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

        A RATIFIED POSITION OUTRANKS A STORED PASSAGE ON THE SAME CITATION.
        The passage lookup used to come first unconditionally, so a secondary or
        tertiary source carrying both stored text and a position the firm had
        taken on it reached the engine as non-binding authority and refused with
        `authority_permits_choice` -- which is the very escalation that CREATES
        a position. The record already held the answer and refused to use it.
        The firm is the last layer; where they have spoken, their words are the
        authority and the commentary underneath them is not.
        """
        if (pos := self.position(citation)) is not None:
            src = next((s for s in self.sources
                        if from_source(citation, s.citation_prefix)), None)
            return "position", pos, src
        if (p := self.passage(citation)) is not None:
            return "passage", p, self.source(p.source_id)
        return None


# ── parsing ───────────────────────────────────────────────────────────────────

_HEAD = re.compile(r"^## (\S+) · (.+)$", re.M)
_SUBJ_HEAD = _HEAD
_BARE_HEAD = re.compile(r"^## (.+)$", re.M)


def _blocks(text: str, pattern: re.Pattern) -> list[tuple[re.Match, str]]:
    heads = list(pattern.finditer(text))
    return [
        (h, text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)])
        for i, h in enumerate(heads)
    ]


#: Where a standalone field stops: the next field, the next block, or the end.
_FIELD_END = re.compile(r"^(?:\*\*|## |---\s*$)", re.M)


def _field(block: str, label: str, where: str, *, required: bool = True) -> str:
    """Read a standalone field, INCLUDING the lines it wraps onto.

    This took only the first line. A model's `Working` is chain-of-thought and
    routinely several lines, so the queue kept the first and dropped the rest --
    and the whole reason a refusal is retained is that its reasoning is the
    evidence of what the record is missing. Canon had this identical bug in the
    identical place: a single-line reader on a field that had grown, parsing 5 of
    24 subjects and reporting success. A silent partial read is worse than an
    error, because nothing downstream can tell it happened.
    """
    m = re.search(rf"^\*\*{re.escape(label)}:\*\*[ ]?(.*)$", block, re.M)
    if m:
        rest = block[m.end():]
        stop = _FIELD_END.search(rest)
        value = (m.group(1) + (rest[:stop.start()] if stop else rest)).strip()
        if value:
            return value
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
    """A real day, not a string shaped like one.

    The regex accepts 2026-02-31, which then reached `date.fromisoformat` inside
    `staleness.check` and crashed the report instead of failing the load. This
    parser's whole promise is that a malformed record fails while being read, so
    a check that stops at the digit layout is the promise half-kept.
    """
    if not _DATE.match(value):
        raise RecordError(f"{where}: {label} is {value!r}; must be YYYY-MM-DD")
    try:
        _date_cls.fromisoformat(value)
    except ValueError as exc:
        raise RecordError(
            f"{where}: {label} is {value!r}, which is not a day on the calendar "
            f"({exc}); a date that only looks right fails later, somewhere else"
        ) from exc
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

    # A SET WOULD HIDE A DUPLICATE, AND `Desk.source()` TAKES THE FIRST MATCH. So
    # defining one id twice let a passage's binding tier, access policy and
    # storage permission change by reordering two blocks in SOURCES.md -- with
    # every test still green, because the id was "known" either way.
    seen_ids = set()
    for s_ in sources:
        if s_.id in seen_ids:
            raise RecordError(
                f"SOURCES.md defines {s_.id!r} more than once; which block wins "
                f"would decide the tier and the storage rule, by file order"
            )
        seen_ids.add(s_.id)

    # The same defect one level down: two extracted files defining one citation
    # both load, and `Desk.passage()` takes the first. Files are read sorted, so
    # RENAMING one changes which source, tier and checked date back an answer --
    # and a tier change can turn a served answer into authority_permits_choice.
    seen_citations = set()
    for p in passages:
        if p.citation in seen_citations:
            raise RecordError(
                f"{p.citation!r} is stored more than once in extracted/; which "
                f"copy answers would be decided by filename order"
            )
        seen_citations.add(p.citation)

    known = seen_ids
    for p in passages:
        if p.source_id not in known:
            raise RecordError(
                f"passage {p.citation!r} cites source {p.source_id!r}, which is not "
                f"in SOURCES.md; authority with no recorded source is unverifiable"
            )

    # A POSITION MUST RESOLVE TO EXACTLY ONE SOURCE, CHECKED HERE AND NOT LATER.
    # Positions are matched to their source by citation prefix rather than by an
    # id, so a mistyped citation resolved to nothing and `authority_for` handed
    # back `("position", pos, None)`. The desk loaded clean and then raised
    # EngineError the first time anybody asked that exact question -- a record
    # that reads as valid and detonates on use. Two sources whose prefixes both
    # match is the same defect wearing the other face: the tier served would
    # depend on file order.
    # The third face of the same defect, and the worst of them: `position()`
    # takes the first match, so two RATIFIED positions on one citation meant a
    # filename decided which conclusion the desk served as the firm's. Proposals
    # may collide freely -- competing proposals are what a pull request is for.
    ratified = set()
    for q in pos:
        if q.proposed:
            continue
        if q.citation in ratified:
            raise RecordError(
                f"two ratified positions cite {q.citation!r}; the firm's served "
                f"conclusion would be decided by filename order"
            )
        ratified.add(q.citation)

    for q in pos:
        matched = [s for s in sources
                   if from_source(q.citation, s.citation_prefix)]
        if len(matched) != 1:
            raise RecordError(
                f"position {q.id} cites {q.citation!r}, which matches "
                f"{len(matched)} recorded sources ({[s.id for s in matched]}); a "
                f"position must rest on exactly one, or it cannot be served"
            )

    subjects = desk_dir / "SUBJECTS.md"
    fires_on, answered_from = (), {}
    if subjects.is_file():
        reg = parse_subjects(subjects.read_text(encoding="utf-8"), desk_dir.name)
        fires_on, answered_from = reg.fires_on, reg.answered_from
        unknown = sorted(set(answered_from) - {s.id for s in sources})
        if unknown:
            raise RecordError(
                f"{desk_dir.name}/SUBJECTS.md answers subjects from {unknown}, "
                f"which SOURCES.md does not define. A mapping to a source that "
                f"does not exist refuses every citation for those subjects")

    return Desk(
        name=desk_dir.name,
        fires_on=fires_on,
        answered_from=answered_from,
        sources=tuple(sources),
        passages=tuple(passages),
        problems=tuple(problems),
        positions=tuple(pos),
    )


def _read(path: Path) -> str:
    if not path.is_file():
        raise RecordError(f"no {path.name} at {path.parent}")
    return path.read_text(encoding="utf-8")
