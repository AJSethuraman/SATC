"""One pool, keyed by the citation, searched over the authority's own words.

WHAT THIS REPLACES, AND WHY THE FIRM KILLED IT. `routing.py` decides which desk
a question reaches by matching it against a word list somebody wrote next to the
desk's name. On 8 September 2026 the firm ended that on a measurement rather
than an argument -- the deposits question written six ways reached no desk three
times and the WRONG desk twice:

    "are unidentified deposits gross receipts?"  ->  meals-and-entertainment

because `receipts` sits on the meals desk meaning *the paper you keep*, while
the question meant *revenue*. Forge-Occam's line was **"The word that saved me
was 'bank'."** `dec-kill`: *"Kill the desks; one pool."*

    What DIES:     the word-matching that decides which desk a question reaches.
    What SURVIVES: everything stored against the CITATION rather than the desk --
                   the ratified positions, the per-citation narrowing, the second
                   reader, and fetching live from the publisher.

So this module holds no desks. It holds citations, and it finds them by asking
whether the question's words appear IN THE AUTHORITY ITSELF. Pub. 583 says
"supporting documents" and "kinds of records to keep" in its own text; nobody
has to remember to write those words next to a desk called `cash-and-bank`, and
a bookkeeper who never types "bank" still reaches it.

THIS IS NOT A JUDGEMENT AND NO MODEL MAKES IT. Same line `routing` drew and for
the same reason (C8): "does this question's language appear in this passage" is
a comparison. It is deterministic, it is re-runnable, and a wrong hit is a
defect somebody can point at rather than an opinion.

SILENCE IS STILL A RESULT. A question sharing no substantive word with anything
in the pool returns nothing -- not a nearest guess. `routing`'s docstring is
right that a router which always answers is one whose answer means nothing, and
killing the word list does not change that.

THE POOL RANKS AND DOES NOT CHOOSE. `receipts` is genuinely three words at once
-- a meals-substantiation term, a gross-receipts term, and the ordinary word for
proof of purchase -- and no retrieval fixes that, because it is a fact about
English rather than a defect. What the pool does differently is RETURN BOTH,
scored, instead of returning only whichever one a human happened to write down.
Deciding between them is `engine`'s job and, where nothing settles it, the
firm's.

DESK NAMES ARE PROVENANCE, NEVER A KEY. Each entry records the folder its record
was read from, because a hole has to be reportable to somewhere. Nothing in the
matching path may read it, and `test_the_pool_never_matches_on_a_desk_name`
exists to keep that true as this file grows.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import record


#: Words that carry no subject. Deliberately SHORT and closed: every word here
#: is one the pool cannot see, so a long list is a second vocabulary of the kind
#: this module exists to delete. These are function words -- no term of art, no
#: accounting word, nothing a firm would ever have to maintain.
STOPWORDS = frozenset("""
a an the this that these those it its is are was were be been being am
do does did doing done can could should would will shall may might must
of in on at to for from by with without into onto about as than then
and or but if so because we us our you your they them their he she him her
i me my what which who whom whose when where why how
not no nor any some all both each more most other such only own same
have has had having get got go goes going
there here up down out over under again further once
""".split())

_WORD = re.compile(r"[a-z0-9][a-z0-9.\-/§]*", re.I)


@dataclass(frozen=True)
class Held:
    """One piece of authority in the pool, addressed by its citation.

    `text` is what the matching reads and it is the AUTHORITY'S OWN WORDS --
    never a description of them, never a subject line somebody wrote. Where a
    licence forbids storing the text (FASB ASC, whose content may not reach a
    model at all) `text` is empty and the entry is still held: the firm's
    ratified position on it is the pool's entire knowledge of that citation, and
    dropping the entry would make the position unreachable. Such an entry can
    only ever be found by a caller that already knows the citation, which is the
    honest outcome -- an unreadable source cannot be retrieved by its contents.
    """
    citation: str
    #: RULE or EXAMPLE, carried through from the record unchanged. `ask` prints
    #: everything and `ask.brief_for_grading` prints no example, and that split
    #: has to survive the move into the pool or the corpus leaks its answer key
    #: again (`runs/2026-09-04/SCOREBOARD.md`).
    kind: str
    text: str
    source_id: str
    #: The publisher's tier for this citation -- primary, secondary, tertiary.
    tier: str
    url: str
    #: PROVENANCE ONLY. Which desk folder this was read from, so a hole can be
    #: reported somewhere and a record can be found again on disk. THE MATCHING
    #: PATH MAY NOT READ THIS.
    read_from: str
    #: The firm's ratified positions resting on this citation, carried across so
    #: `alongside` keeps working: `cash-and-bank` holds two positions on one
    #: section of Pub. 583 with OPPOSITE answers, and serving one without the
    #: other is the 7 September incident.
    positions: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class Found:
    """One hit, with the arithmetic that produced it kept rather than summarised.

    `matched` is the actual words that overlapped. Behaviour: earn the claim --
    a score with nothing under it is a number a reader has to trust, and the
    whole point of killing the word list was that a wrong hit should be
    something somebody can point at.
    """
    held: Held
    score: float
    matched: tuple[str, ...]


def terms(text: str) -> tuple[str, ...]:
    """The substantive words of a piece of text, in order, lowercased."""
    return tuple(w.group(0).lower() for w in _WORD.finditer(text)
                 if w.group(0).lower() not in STOPWORDS)


def assemble(desks_dir: Path) -> tuple[Held, ...]:
    """Every citation on file, from every record, as one pool.

    Reads the same folders `routing.registry` reads and throws away the only
    thing `routing` uses them for. The folders survive as where the records are
    WRITTEN; they stop being how a question is answered.
    """
    held: list[Held] = []
    for folder in sorted(Path(desks_dir).iterdir()):
        if not (folder / "SUBJECTS.md").is_file():
            continue
        desk = record.load(folder)
        by_citation: dict[str, list] = {}
        for position in desk.positions:
            if not getattr(position, "proposed", False):
                by_citation.setdefault(position.citation, []).append(position)
        seen = set()
        for passage in desk.passages:
            source = desk.source(passage.source_id)
            held.append(Held(
                citation=passage.citation,
                kind=passage.kind,
                text=passage.text,
                source_id=passage.source_id,
                tier=getattr(source, "tier", "") if source else "",
                url=getattr(source, "url", "") if source else "",
                read_from=folder.name,
                positions=tuple(by_citation.get(passage.citation, ())),
            ))
            seen.add(passage.citation)
        # A citation the firm took a position on but whose text is not stored --
        # a licence forbids it, or nobody has extracted it yet. Held with empty
        # text so the position stays reachable by citation. See `Held.text`.
        for citation, positions in sorted(by_citation.items()):
            if citation in seen:
                continue
            held.append(Held(citation=citation, kind=record.RULE, text="",
                             source_id="", tier="", url="",
                             read_from=folder.name, positions=tuple(positions)))
    return tuple(held)


#: BM25's two constants. `K1` is where a repeated word stops helping -- the
#: fourth "deposit" in a passage says little the third did not. `B` is how hard
#: length is penalised: 0 ignores length entirely, 1 divides it out fully.
#:
#: B IS 0.6 AND THAT IS A MEASUREMENT, NOT A TASTE. The first version of this
#: file normalised by sqrt(length) instead, which is B pushed past 1, and the
#: top hit for *"what receipts do we need to keep?"* was a ten-word fragment --
#: "Multiplying the gross receipts for the short period by 12; and" -- while
#: Pub. 583's thousand-word "Supporting Documents" section, which is the actual
#: answer, did not place. This corpus runs from 1 term to 630 in one pool, so
#: over-penalising length is not a small error here.
K1 = 1.2
B = 0.6


@dataclass(frozen=True)
class _Stats:
    """What the corpus knows about itself: how rare each word is, how long the
    average passage runs. Computed once and passed down, because recomputing it
    per question turned a 794-entry pool into a per-call scan of the corpus."""
    idf: dict
    avg_len: float


def stats(pool: tuple[Held, ...]) -> _Stats:
    """How much each word narrows the pool. A word in everything says nothing.

    Inverse document frequency, BM25's form. `expense` appears across most of
    the corpus and is close to worthless for finding anything; `odometer`
    appears in one place and is nearly decisive. THIS IS THE PART A HAND-WRITTEN
    WORD LIST CANNOT DO: it is measured from the corpus rather than judged by
    whoever was writing the desk that day, and it changes on its own when a
    source is added -- nobody has to remember to update it.
    """
    lengths = [len(terms(e.text)) for e in pool]
    n = len(pool) or 1
    seen: dict[str, int] = {}
    for entry in pool:
        for word in set(terms(entry.text)):
            seen[word] = seen.get(word, 0) + 1
    idf = {w: math.log(1 + (n - df + 0.5) / (df + 0.5)) for w, df in seen.items()}
    return _Stats(idf=idf, avg_len=(sum(lengths) / n) or 1.0)


def look(question: str, pool: tuple[Held, ...], *, limit: int = 8,
         known: "_Stats | None" = None) -> tuple[Found, ...]:
    """What in the pool speaks to this question. Possibly nothing.

    Scored by BM25 over the authority's own text: how much of the question's
    language appears in it, weighted by how rare each word is in this corpus,
    with a repeated word saturating (`K1`) and length discounted against the
    corpus average rather than divided out (`B`).

    Ordered by score, then by citation, so the same question gives the same
    answer in the same order on every run and a change in the ordering is a
    change somebody made.
    """
    corpus = stats(pool) if known is None else known
    asked = set(terms(question))
    if not asked:
        return ()
    out: list[Found] = []
    for entry in pool:
        words = terms(entry.text)
        if not words:
            continue
        present = asked & set(words)
        if not present:
            continue
        norm = K1 * (1 - B + B * len(words) / corpus.avg_len)
        score = 0.0
        for word in present:
            tf = words.count(word)
            score += corpus.idf.get(word, 0.0) * tf * (K1 + 1) / (tf + norm)
        if score <= 0:
            continue
        out.append(Found(held=entry, score=score,
                         matched=tuple(sorted(present))))
    out.sort(key=lambda f: (-f.score, f.held.citation))
    return tuple(out[:limit])
