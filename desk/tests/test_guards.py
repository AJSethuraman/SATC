"""The record's gates. They fail the build; they do not warn.

Each guard exists because review discipline is not a mechanism: a rule that
depends on somebody noticing a line in a diff holds until the first busy
afternoon, and then it holds nowhere and nobody knows when it stopped.
"""
from __future__ import annotations

import pytest

import guards
import record
from conftest import DESKS

GOOD_SOURCE = ("## S1 · A source\n\n"
               "**Tier:** primary · **Access:** public_fetch · "
               "**May store:** full_text · **Checked:** 2026-09-04\n\n"
               "**Citation prefix:** 26 CFR\n\n"
               "**Why:** 17 U.S.C. § 105 places a work of the United States "
               "Government in the public domain.\n")
GOOD_PROBLEM = ("## P1 · x\n\n**Citation:** 26 CFR 1\n\n"
                "**Answer:** must capitalize\n\n**Facts:** f\n")
GOOD_PASSAGE = ("## 26 CFR 1\n\n**Source:** S1 · **Checked:** 2026-09-04\n\n"
                "> must capitalize\n")


GOOD_POSITION = ("## POS1 · What we do here\n\n"
                 "**Citation:** 26 CFR 1 · **Recorded:** 2026-09-04\n\n"
                 "**Position:** must capitalize\n\n"
                 "**Ratified:** the firm, 4 September 2026\n")


def build(tmp_path, *, source=GOOD_SOURCE, problem=GOOD_PROBLEM,
          passage=GOOD_PASSAGE, position=None, name="d"):
    d = tmp_path / name
    (d / "extracted").mkdir(parents=True)
    (d / "SOURCES.md").write_text(source, encoding="utf-8")
    (d / "PROBLEMS.md").write_text(problem, encoding="utf-8")
    if passage is not None:
        (d / "extracted" / "a.md").write_text(passage, encoding="utf-8")
    if position is not None:
        (d / "positions").mkdir(parents=True)
        (d / "positions" / "POSITIONS.md").write_text(position, encoding="utf-8")
    return d


# ── the control, without which every test below could pass for the wrong reason ──

def test_a_well_formed_desk_passes_every_guard(tmp_path):
    assert guards.check(build(tmp_path)).name == "d"


def test_the_shipped_desk_passes_every_guard():
    """The one that actually matters: the record in this repo is legal."""
    assert guards.check(DESKS / "fixed-assets")


# ── a judgement must not ride along inside an extraction ─────────────────────

@pytest.mark.parametrize("marker", ["Position", "Ratified"])
def test_a_position_hidden_in_an_extraction_fails_the_build(tmp_path, marker):
    """A large extraction diff is skimmed and a single position is read. A
    position inside the first is one that got ratified by a glance."""
    d = build(tmp_path, passage=GOOD_PASSAGE + f"\n**{marker}:** we capitalise\n")
    with pytest.raises(guards.GuardFailure, match=marker):
        guards.check(d)


# ── nothing is stored from a source that does not permit storing ─────────────

@pytest.mark.parametrize("may_store", ["citation_only", "license_check"])
def test_storing_text_under_a_restricted_source_fails_the_build(
        tmp_path, may_store):
    d = build(tmp_path, source=GOOD_SOURCE.replace("full_text", may_store))
    with pytest.raises(guards.GuardFailure, match="may_store"):
        guards.check(d)


def test_license_check_is_the_default_and_it_stores_nothing():
    """A licence the firm holds may permit a copy, which is why this is a fact
    per source rather than one policy over all of them."""
    assert record.MAY_STORE[-1] == "license_check"


# ── human_only is the absence of a fetch ─────────────────────────────────────

def test_stored_text_from_a_human_only_source_fails_the_build(tmp_path):
    """The engine never reaches for it, so this text cannot have arrived by a
    permitted route. FASB ASC is the worked example."""
    d = build(tmp_path, source=GOOD_SOURCE.replace("public_fetch", "human_only"))
    with pytest.raises(guards.GuardFailure, match="human_only"):
        guards.check(d)


def test_a_human_only_source_is_reachable_only_through_a_ratified_position(tmp_path):
    """Cited by reference, never read -- but "never read" is not "no authority".

    The guard used to wave a `human_only` citation through on the strength of its
    SOURCE being unreadable, which is a different question from whether the desk
    holds anything. With no position for that exact citation, `authority_for`
    still returns None, so every attempt at the problem graded
    `wrong_caught / authority_absent`: a row in the denominator that nothing
    could ever answer.
    """
    d = build(tmp_path,
              source=GOOD_SOURCE.replace("public_fetch", "human_only"),
              passage=None, position=GOOD_POSITION)
    assert guards.check(d)


def test_a_human_only_citation_with_no_position_is_not_authority(tmp_path):
    """The case the old guard admitted. Unanswerable, and counted as a problem."""
    d = build(tmp_path,
              source=GOOD_SOURCE.replace("public_fetch", "human_only"),
              passage=None)
    with pytest.raises(guards.GuardFailure, match="resolves to no authority"):
        guards.check(d)


# ── a storage permission is a claim about a licence, and carries its term ────

def test_permission_to_store_with_no_licence_term_fails_the_build(tmp_path):
    """`may_store` above `license_check` is a claim about somebody else's terms.

    A claim with no term behind it is a guess that reaches outside this
    repository, and the whole point of recording the permission per source is
    that it was READ rather than assumed.
    """
    d = build(tmp_path, source=GOOD_SOURCE[:GOOD_SOURCE.index("\n\n**Why:**")] + "\n")
    with pytest.raises(guards.GuardFailure, match="no 'Why'"):
        guards.check(d)


def test_license_check_needs_no_term_because_it_stores_nothing(tmp_path):
    """The default is the one permission that needs no evidence."""
    d = build(tmp_path,
              source=(GOOD_SOURCE.replace("full_text", "license_check")
                      .replace("\n\n**Why:** 17 U.S.C. § 105 places a work of "
                               "the United States Government in the public "
                               "domain.\n", "\n")),
              passage=None, position=GOOD_POSITION)
    assert guards.check(d)


# ── the authority corpus must not be the answer key ──────────────────────────

def test_a_corpus_that_is_exactly_the_answer_key_fails_the_build(tmp_path):
    """Measured on fixed-assets, 4 Sep 2026: 21 problems, 21 stored passages,
    the same citation on both sides. Citing correctly was an assignment puzzle,
    so the run's citation number could not be read at all (#244)."""
    two_problems = (GOOD_PROBLEM
                    + "\n## P2 · y\n\n**Citation:** 26 CFR 2\n\n"
                      "**Answer:** must capitalize\n\n**Facts:** g\n")
    two_passages = (GOOD_PASSAGE
                    + "\n## 26 CFR 2\n\n**Source:** S1 · "
                      "**Checked:** 2026-09-04\n\n> must capitalize\n")
    d = build(tmp_path, problem=two_problems, passage=two_passages)
    with pytest.raises(guards.GuardFailure, match="authority corpus IS the answer key"):
        guards.check(d)


def test_one_rule_stored_beside_the_keyed_ones_is_enough(tmp_path):
    """The bijection is the defect, not the overlap. A corpus that holds
    anything the problems are not keyed to is retrieval again."""
    two_problems = (GOOD_PROBLEM
                    + "\n## P2 · y\n\n**Citation:** 26 CFR 2\n\n"
                      "**Answer:** must capitalize\n\n**Facts:** g\n")
    three_passages = (GOOD_PASSAGE
                      + "\n## 26 CFR 2\n\n**Source:** S1 · "
                        "**Checked:** 2026-09-04\n\n> must capitalize\n"
                      + "\n## 26 CFR 3\n\n**Source:** S1 · "
                        "**Checked:** 2026-09-04\n\n> some other rule\n")
    d = build(tmp_path, problem=two_problems, passage=three_passages)
    assert guards.check(d)


def test_a_one_problem_tracer_is_exempt_because_there_is_nothing_to_assign(tmp_path):
    """#221's tracer desk is one problem and one passage. That is a bijection
    with no assignment in it, and failing it would make the guard fire on the
    smallest honest desk there is."""
    assert guards.check(build(tmp_path))


# ── a problem the desk cannot support cannot be scored honestly ──────────────

def test_a_problem_citing_authority_the_desk_lacks_fails_the_build(tmp_path):
    d = build(tmp_path, problem=GOOD_PROBLEM.replace("26 CFR 1", "26 CFR 9"))
    with pytest.raises(guards.GuardFailure, match="resolves to no authority"):
        guards.check(d)


# ── positions parse, and an unratified one says so ───────────────────────────

def test_a_position_carries_the_firms_words_and_its_authority():
    ps = positions_parse(
        "## POS1 · Roof replacement\n\n"
        "**Citation:** 26 CFR 1 · **Recorded:** 2026-09-04\n\n"
        "**Position:** we capitalise a full roof replacement\n\n"
        "**Ratified:** PR #999\n")
    assert ps[0].position.startswith("we capitalise")
    assert not ps[0].proposed


def test_an_unratified_position_is_marked_proposed():
    """Real when a person merges it, and not before."""
    ps = positions_parse(
        "## POS1 · x\n\n**Citation:** c · **Recorded:** 2026-09-04\n\n"
        "**Position:** p\n")
    assert ps[0].proposed


def positions_parse(text):
    import positions
    return positions.parse(text)
