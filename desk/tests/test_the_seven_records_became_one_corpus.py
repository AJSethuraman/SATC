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
  a truncation. `26 CFR 1.274-5T(a)` was 1,466 characters on `meals-and-
  entertainment` and 125 on `vehicle-expense`, so a vehicle question answered
  from it was served a TWELFTH of the rule and nothing could see it, because a
  question only ever reached one desk. (Those two figures read 1,551 and 210
  here until 10 September 2026 and were the block lengths, heading and source
  line included, rather than the rule's; the ones above are `len(passage.text)`
  and come out of the frozen inventory.)

THE LAST ONE IS THE ARGUMENT FOR THE MERGE and it is asserted below by name. A
future edit that reintroduces a short copy of one of those passages puts the
truncation back, and nothing else in the suite would notice.
"""

import json
from pathlib import Path

import pytest

import pool
import record


DESK = Path(__file__).resolve().parent.parent
CORPUS = DESK / "corpus"
#: THE SEVEN, AS THEY STOOD THE DAY THEY WERE DELETED. This read `desks/` off
#: disk until 10 September 2026; the firm said to delete that directory and it
#: is gone, so the inventory this file compares against is FROZEN rather than
#: re-derived. The file was written from the working tree by
#: `tests/fixtures/build_seven.py` immediately before `git rm -r desks/`, and
#: the git history holds the records themselves if anyone needs the text.
#:
#: A frozen INVENTORY is honest where a frozen ASSERTION would not be: this is a
#: record of what existed, and the live corpus is checked against it. Nothing
#: here re-runs the seven or claims to.
SEVEN = Path(__file__).resolve().parent / "fixtures" / "seven-records-2026-09-10.json"


@pytest.fixture(scope="module")
def corpus():
    return record.load(CORPUS)


@pytest.fixture(scope="module")
def seven():
    got = json.loads(SEVEN.read_text(encoding="utf-8"))["records"]
    assert len(got) == 7, f"{len(got)} records in the frozen inventory, not 7"
    return got


def test_the_corpus_loads_as_one_record(corpus):
    """One registration, not seven. This is where the desk actually dies:
    `record.load` refuses a registration named differently from its directory,
    a guard that exists so a refusal can say `ask cash-and-bank`."""
    assert corpus.name == "corpus"


def test_nothing_the_firm_wrote_was_lost(corpus, seven):
    """Every citation, position and problem that existed across the seven."""
    was = {p["citation"] for k in seven for p in k["passages"]}
    assert was <= {p.citation for p in corpus.passages}, (
        sorted(was - {p.citation for p in corpus.passages})[:3])

    # THE FIRM'S WORDS, NOT THE PIN THEY WERE ON. This compared
    # `(citation, position)` pairs, and `dec-pos2` unpinned POS11 from
    # § 1.262-1(a) — two independent judges refused that pairing, and the firm
    # answered "Firm policy, no citation". Not one word of any position changed.
    # So what "nothing was lost" means for a position is checked on the words,
    # and the ONE citation that moved is named rather than allowed for.
    was_p = {q[1] for k in seven for q in k["positions"]}
    assert was_p <= {q.position for q in corpus.positions}

    moved = {q[0] for k in seven for q in k["positions"]} - {
        q.citation for q in corpus.positions}
    assert moved == {"26 CFR 1.262-1(a) — the general rule"}, (
        f"a position's citation moved and it is not the one `dec-pos2` moved: "
        f"{sorted(moved)}. Repinning a ratified position is the firm's, and it "
        f"belongs in the commit that does it.")

    was_b = {b for k in seven for b in k["problems"]}
    assert was_b <= {b.id for b in corpus.problems}

    was_s = {s for k in seven for s in k["sources"]}
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
        for citation, terms in k["answered_by"].items():
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


#: THE SIX CITATIONS TWO RECORDS STORED WITH DIFFERENT TEXT. A roster of WHICH,
#: from the merge's own output. It carried a length beside each until
#: 10 September 2026 and the lengths were wrong — they were block lengths, and
#: the test below never used them. The comparison reads the frozen inventory, so
#: there is nothing here to go stale.
LONGEST = (
    "26 CFR 1.162-3(c)(1)(i)",
    "26 CFR 1.162-3(c)(2)",
    "26 CFR 1.274-5T(a)",
    "26 CFR 1.274-5T(b)(1)",
    'IRS Pub. 463 (2025), "What Are Adequate Records?"',
    'IRS Pub. 463 (2025), "Proving business purpose"',
)


@pytest.mark.parametrize("citation", sorted(LONGEST))
def test_the_truncated_copy_did_not_win(citation, seven, corpus):
    """The finding the merge produced, pinned so it cannot come back.

    Asserted against the SEVEN, not against a number typed into this file: the
    corpus must hold at least as much of the rule as the longest copy any record
    held. `LONGEST` above is a roster of WHICH citations were doubled, not the
    comparison — the lengths come out of the frozen inventory.
    """
    held = [p["chars"] for k in seven for p in k["passages"]
            if p["citation"] == citation]
    assert len(held) > 1, f"{citation!r} was not stored twice; test is stale"
    longest = max(held)
    now = next((p.text for p in corpus.passages if p.citation == citation), None)
    assert now is not None, f"{citation!r} is not in the corpus at all"
    assert len(now) >= longest, (
        f"the corpus holds {len(now)} characters of {citation!r} and one of the "
        f"seven records held {longest} — a truncation won the merge"
    )


def test_the_pool_holds_one_entry_per_citation(corpus):
    """THE MIGRATION SEAM IS GONE AND SO IS THE TEST THAT STRADDLED IT.

    This read both shapes — `pool.assemble(CORPUS)` and `pool.assemble(DESKS)` —
    and asserted the corpus held FEWER entries, the difference being the
    duplicates it resolved. `desks/` no longer exists, so half of that
    comparison cannot run. The numbers it produced are in the frozen inventory
    (794 rows across the seven) and in `tools/one_corpus.py`'s own report.

    What survives is the property the comparison was FOR: one entry per
    citation, which is what having resolved the duplicates means.
    """
    entries = pool.assemble(CORPUS)
    citations = [h.citation for h in entries]
    assert len(citations) == len(set(citations)), (
        "a citation is in the pool twice, so the duplicate resolution the merge "
        "performed has been undone")
    # ONE MORE ENTRY THAN THERE ARE PASSAGES, SINCE `dec-pos2`. A firm-policy
    # position is a citation the pool holds with no stored text behind it —
    # there is no publisher to have stored any — and it is findable on the
    # position's own words, which is how a reviewer reaches it. The relation
    # that must hold is that every passage is in the pool and nothing is in the
    # pool twice; an equality here was only ever true while every citation had
    # a passage.
    assert {p.citation for p in corpus.passages} <= set(citations)
    policies = [q.citation for q in corpus.positions
                if not q.proposed and getattr(q, "is_policy", False)]
    assert len(entries) == len(corpus.passages) + len(policies), (
        f"{len(entries)} pool entries for {len(corpus.passages)} passages and "
        f"{len(policies)} firm policies")

    # And Forge-Occam's substantiation question, which under the word list
    # reached NOTHING, still reaches the authority their desk said it wanted.
    question = "what supporting documents does the client have to keep?"
    top = pool.look(question, entries, limit=1, known=pool.stats(entries))
    assert top and top[0].held.citation.startswith("IRS Pub. 583")


def test_the_seven_held_more_rows_than_the_corpus_holds_citations(seven):
    """The dedupe, from the frozen inventory: 794 rows of stored authority
    across the seven, 785 distinct citations, and the nine are the ones two
    desks each held.

    "794" is deliberately not written as a corpus SIZE here —
    `test_the_corpus_figure_is_not_typed_anywhere.py` sweeps every file for a
    three-digit number beside the word "passages" and reports it against what
    the record actually holds, which is 785. It is right to: 794 is a fact about
    seven records that no longer exist, and a reader meeting it in that phrasing
    would take it for today's count.
    """
    rows = [p["citation"] for k in seven for p in k["passages"]]
    assert len(rows) == 794
    assert len(set(rows)) == 785
    doubled = {c for c in rows if rows.count(c) > 1}
    assert len(doubled) == 9
    assert set(LONGEST) <= doubled, (
        "the six citations stored with DIFFERENT text must be among the nine "
        "stored twice")


def test_provenance_says_corpus_and_nothing_matches_on_it(corpus):
    """`read_from` is provenance so a hole can be reported somewhere. Over the
    corpus it is one value, which makes it useless as a key — which is the
    point."""
    entries = pool.assemble(CORPUS)
    assert {h.read_from for h in entries} == {"corpus"}
