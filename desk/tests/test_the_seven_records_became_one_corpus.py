"""The seven records are one corpus, and nothing the firm wrote was lost.

    `dec-kill`, 8 September 2026 -- "Kill the desks; one pool."
    10 September, twice -- "I said to delete them. I've said to multiple
    times." / "I do not care. One corpus."

`tools/one_corpus.py` did the merge and printed what it did. This is the part
that has to keep being true afterwards, so it is asserted here rather than left
in a tool's output that nobody re-runs.

WHAT THE MERGE HAD TO RESOLVE, all of it measured rather than assumed:

  36 source rows shared 15 ids -- `S1` named a different publication on each of
  seven desks. 33 distinct sources, renumbered, every reference rewritten.

  3 sources were declared by two records each WITH DIFFERENT SUBJECT LISTS.
  Unioned, because both lists are true of the same regulation and `record.load`
  refuses the duplicate outright ("which list wins would be decided by file
  order").

  9 citations were held twice and 6 of those stored DIFFERENT TEXT -- every one
  a truncation. `26 CFR 1.274-5T(a)` was 1,551 characters on one record and 210
  on another, so a vehicle question answered from it was served a seventh of the
  rule and nothing could see it, because a question only ever reached one desk.

THE LAST ONE IS THE ARGUMENT FOR THE MERGE and it is asserted below by name. A
future edit that reintroduces a short copy of one of those passages puts the
truncation back, and nothing else in the suite would notice.
"""

from pathlib import Path

import pytest

import pool
import record


DESK = Path(__file__).resolve().parent.parent
CORPUS = DESK / "corpus"
DESKS = DESK / "desks"


@pytest.fixture(scope="module")
def corpus():
    return record.load(CORPUS)


@pytest.fixture(scope="module")
def seven():
    return [record.load(d) for d in sorted(DESKS.iterdir())
            if (d / "SUBJECTS.md").is_file()]


def test_the_corpus_loads_as_one_record(corpus):
    """One registration, not seven. This is where the desk actually dies:
    `record.load` refuses a registration named differently from its directory,
    a guard that exists so a refusal can say `ask cash-and-bank`."""
    assert corpus.name == "corpus"


def test_nothing_the_firm_wrote_was_lost(corpus, seven):
    """Every citation, position and problem that existed across the seven."""
    was = {p.citation for k in seven for p in k.passages}
    assert was <= {p.citation for p in corpus.passages}, (
        sorted(was - {p.citation for p in corpus.passages})[:3])

    was_p = {(q.citation, q.position) for k in seven for q in k.positions}
    assert was_p <= {(q.citation, q.position) for q in corpus.positions}

    was_b = {b.id for k in seven for b in k.problems}
    assert was_b <= {b.id for b in corpus.problems}

    was_s = {s.title.strip() for k in seven for s in k.sources}
    assert was_s <= {s.title.strip() for s in corpus.sources}


def test_the_per_citation_narrowing_survived(corpus, seven):
    """`dec-kill` names it as surviving, and it is the one check in the engine
    that still BLOCKS: two paragraphs of one publication carrying opposite
    answers is the opposite treatment of the same money. The 5 September
    incident -- a service charge served with the timing citation,
    `checked_subject=True`, real source and wrong paragraph -- is what it stops.
    """
    was = {}
    for k in seven:
        for citation, terms in k.answered_by.items():
            was.setdefault(citation, set()).update(terms)
    assert was, "no record declared a narrowing; this test proves nothing"
    now = {c: set(t) for c, t in corpus.answered_by.items()}
    for citation, terms in was.items():
        assert citation in now, f"narrowing lost for {citation!r}"
        assert terms <= now[citation], f"narrowing weakened for {citation!r}"


def test_every_source_id_is_distinct(corpus):
    """The collision the merge existed to fix. Before it, `S1` named seven
    different publications and the id said nothing on its own."""
    ids = [s.id for s in corpus.sources]
    assert len(ids) == len(set(ids)), "a source id is used twice"


def test_every_passage_names_a_source_the_corpus_holds(corpus):
    """The renumbering's silent failure mode, and the reason it is checked.

    A missed `**Source:** Sn` rewrite does not crash -- it leaves a passage
    pointing at whichever publication now carries that id, which is worse than
    a crash because it still loads and still serves.
    """
    ids = {s.id for s in corpus.sources}
    orphan = sorted({p.citation for p in corpus.passages
                     if p.source_id not in ids})
    assert not orphan, f"{len(orphan)} passages name a missing source: {orphan[:3]}"


#: The six citations two records stored with different text, and the length of
#: the version that WON. Taken from the merge's own output, not from memory.
LONGEST = {
    "26 CFR 1.162-3(c)(1)(i)": 338,
    "26 CFR 1.162-3(c)(2)": 677,
    "26 CFR 1.274-5T(a)": 1551,
    "26 CFR 1.274-5T(b)(1)": 420,
    'IRS Pub. 463 (2025), "What Are Adequate Records?"': 1732,
    'IRS Pub. 463 (2025), "Proving business purpose"': 920,
}


@pytest.mark.parametrize("citation", sorted(LONGEST))
def test_the_truncated_copy_did_not_win(citation, seven, corpus):
    """The finding the merge produced, pinned so it cannot come back.

    Asserted against the SEVEN, not against a stored number: the corpus must
    hold at least as much of the rule as the longest copy any record held. A
    hard-coded length would go stale the first time a passage is legitimately
    re-extracted; this stays true.
    """
    held = [p.text for k in seven for p in k.passages if p.citation == citation]
    assert len(held) > 1, f"{citation!r} was not stored twice; test is stale"
    longest = max(len(t) for t in held)
    now = next((p.text for p in corpus.passages if p.citation == citation), None)
    assert now is not None, f"{citation!r} is not in the corpus at all"
    assert len(now) >= longest, (
        f"the corpus holds {len(now)} characters of {citation!r} and one of the "
        f"seven records held {longest} — a truncation won the merge"
    )


def test_the_pool_reads_the_corpus_and_the_desks_alike(corpus):
    """The migration seam, and the one question that proves it.

    Forge-Occam's substantiation question, which under the word list reached
    NOTHING. Both shapes must return the same authority — and the corpus must
    hold FEWER entries, because the duplicates are exactly what it resolved.
    """
    from_corpus = pool.assemble(CORPUS)
    from_desks = pool.assemble(DESKS)
    assert len(from_corpus) < len(from_desks), (
        "the corpus should hold fewer entries than the seven records; the "
        "difference is the duplicate citations it deduplicated")

    question = "what supporting documents does the client have to keep?"
    a = pool.look(question, from_corpus, limit=1, known=pool.stats(from_corpus))
    b = pool.look(question, from_desks, limit=1, known=pool.stats(from_desks))
    assert a and b, "the question reached nothing in one of the two shapes"
    assert a[0].held.citation == b[0].held.citation


def test_provenance_says_corpus_and_nothing_matches_on_it(corpus):
    """`read_from` is provenance so a hole can be reported somewhere. Over the
    corpus it is one value, which makes it useless as a key — which is the
    point."""
    entries = pool.assemble(CORPUS)
    assert {h.read_from for h in entries} == {"corpus"}
