"""The 43 questions a real close raised, and the claim made about them.

WHY THIS IS A TEST AND NOT A PARAGRAPH. `docs/CLOSE-QUESTIONS-TRIAGE.md` opens
with a number — 11 of 43 are questions a desk can answer — and that number is the
whole argument. A count asserted in prose beside a table it is supposed to
summarise is a claim nobody re-derives; the first row added or reclassified makes
it silently false, and it is the sentence everybody quotes.

So the counts are read off the table rather than trusted, the questions are read
off the corpus rather than trusted, and the two files are compared against each
other. `docs/` here is not commentary on the work; on this pair of files it is
the work.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
CORPUS = DOCS / "CLOSE-QUESTIONS-2026-09-05.md"
TRIAGE = DOCS / "CLOSE-QUESTIONS-TRIAGE.md"

#: The question set is fixed at 43. It is a real close's real output, so it does
#: not grow to make a number look better -- a denominator that moves is not a
#: denominator. A later close is a NEW corpus with its own file and its own count.
TOTAL = 43

KINDS = ("A", "B", "C", "D", "E", "F")


def _rows() -> list[tuple[int, str, str]]:
    """(number, primary kind, secondary kind) for every row of the big table."""
    out = []
    for line in TRIAGE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|[^|]*\|\s*\*\*([A-F])\*\*\s*\|([^|]*)\|", line)
        if m:
            out.append((int(m.group(1)), m.group(2), m.group(3).strip()))
    return out


def _claimed() -> dict[str, int]:
    """The count table's own numbers, read back out of it."""
    out = {}
    for line in TRIAGE.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*([A-F])\s*·[^|]*\|\s*(\d+)\s*\|", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def test_every_question_in_the_corpus_is_classified():
    """A question that reached the corpus and not the table is one nobody has
    decided the owner of, and it is invisible in every count drawn from it."""
    asked = {int(m) for m in re.findall(r"^\*\*Q(\d+) · ", CORPUS.read_text(
        encoding="utf-8"), re.M)}
    assert len(asked) == TOTAL, f"the corpus holds {len(asked)} questions, not {TOTAL}"

    classified = {n for n, _, _ in _rows()}
    assert classified == asked, (
        f"unclassified: {sorted(asked - classified)}; "
        f"classified but not asked: {sorted(classified - asked)}")


def test_the_counts_are_the_table_and_not_a_memory_of_it():
    """The headline number is computed from the rows, then compared with what the
    summary claims. Written the other way round, the summary IS the source and a
    reclassified row changes nothing anybody can see."""
    counted: dict[str, int] = {k: 0 for k in KINDS}
    for _, primary, _ in _rows():
        counted[primary] += 1

    assert sum(counted.values()) == TOTAL
    assert counted == _claimed(), (
        f"the table says {_claimed()}; its own rows say {counted}")


def test_the_headline_matches_what_the_rows_say():
    """"11 are questions a desk can answer from citable authority" is the
    sentence this file exists to keep true."""
    a = sum(1 for _, primary, _ in _rows() if primary == "A")
    # THE PROSE WRAPS AND THE CLAIM DOES NOT. Matched against the raw file, this
    # passed or failed on where the line break happened to fall rather than on
    # what the sentence said -- the same defect `canon.record._field` was written
    # to fix, arriving here as a test that could not see its own subject.
    flat = " ".join(TRIAGE.read_text(encoding="utf-8").split())
    assert f"**{a} are questions a desk can answer" in flat, (
        f"{a} rows are kind A; the opening paragraph claims otherwise")
    assert f"The other {TOTAL - a} are not authority questions" in flat, (
        f"{TOTAL - a} rows are not kind A; the opening paragraph claims otherwise")


@pytest.mark.parametrize("kind", KINDS)
def test_no_kind_is_empty(kind):
    """A kind nobody used is a distinction that was invented rather than found.
    Every one of these six came from the firm's own words or from the engine's
    existing reason set; if one has no rows, it was neither."""
    assert any(p == kind or kind in s for _, p, s in _rows()), (
        f"kind {kind} classifies nothing")


def test_secondary_kinds_are_real_kinds():
    """A typo in the `Also` column silently drops a second owner."""
    for n, _, secondary in _rows():
        for k in secondary.split():
            assert k in KINDS, f"Q{n} names a second kind {k!r} that does not exist"


def test_a_secondary_kind_is_never_the_primary_one():
    """Naming the same owner twice reads as two owners and is counted as one."""
    for n, primary, secondary in _rows():
        assert primary not in secondary.split(), (
            f"Q{n} lists {primary} as both its primary and its secondary kind")


# ── the queue this corpus actually produced ──────────────────────────────────

def test_only_the_two_kinds_the_queue_holds_were_filed():
    """22 of 43, and the other 21 stayed out.

    THIS IS THE POINT OF THE EXERCISE, not a side effect of it. `from_question`
    takes two reasons because they are the two a question can honestly be in.
    A document request filed as `authority_absent` makes the queue report a gap
    in the record that is not there, and the thing that would actually resolve it
    -- somebody asking for a statement -- is never raised. A queue that accepts
    everything stops meaning anything.
    """
    import unsupported

    queue = Path(__file__).resolve().parents[1] / "unfiled" / "CLOSE-2026-09-05.md"
    entries = unsupported.parse(queue.read_text(encoding="utf-8"))

    expected = {"A": "authority_absent", "B": "facts_not_established"}
    should_file = [n for n, k, _ in
                   ((n, k, s) for n, k, s in _rows()) if k in expected]
    assert len(entries) == len(should_file), (
        f"{len(should_file)} rows are kind A or B; the queue holds {len(entries)}")

    filed = {int(re.match(r"Q(\d+):", u.question).group(1)) for u in entries}
    assert filed == set(should_file), (
        f"missing from the queue: {sorted(set(should_file) - filed)}; "
        f"filed but not kind A or B: {sorted(filed - set(should_file))}")

    by_number = {n: k for n, k, _ in _rows()}
    for u in entries:
        n = int(re.match(r"Q(\d+):", u.question).group(1))
        assert u.failed_because == expected[by_number[n]], (
            f"Q{n} is kind {by_number[n]} and was filed as {u.failed_because}")


def test_every_filed_question_kept_its_reasoning():
    """A question filed as a bare line is one somebody has to re-derive the
    importance of. The reasoning is the best evidence of what is missing, which
    is the entire argument for keeping refusals rather than counting them."""
    import unsupported

    queue = Path(__file__).resolve().parents[1] / "unfiled" / "CLOSE-2026-09-05.md"
    bare = [u.id for u in unsupported.parse(queue.read_text(encoding="utf-8"))
            if not u.working.strip()]
    assert bare == [], f"{bare} were filed with no working"
