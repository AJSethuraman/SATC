"""A position may rest on the firm, and then it says so everywhere it is read.

`dec-pos2`, 10 September 2026 — the firm: **"Firm policy, no citation — with two
conditions."**

WHAT WAS WRONG. POS11 — *"flag it for attention and ask the client what was
bought; do not book it to owner draws on the seller's name"* — was pinned to
26 CFR 1.262-1(a), and two independent judges refused it. They were right: that
paragraph is about costs which are **personal**, and the position is about costs
whose nature is **unknown**. Different questions. The position is sound and the
pin was wrong.

**A WRONG PIN IS WORSE THAN NO PIN.** It tells a reader the regulation says
something it does not, and it survives every check in this repository because
the citation resolves — `authority_for` finds it, `_check` passes it, the
scoreboard scores it. Nothing here could have caught it. Two model readings
did, which is the argument for the second reader in one line.

THE FIRM'S TWO CONDITIONS, verbatim, and each is a mechanism below:

    "I'm good with this but can I want this to be clearly marked as they may
     need to be reviewed/changed at some point. I would also be remiss if
     something I said is my position blatantly goes against a regulation or
     something. I would want the option to review that too though"

  1. CLEARLY MARKED. `Kind: firm policy` on the position, a caveat on every
     answer that leaves, and a paragraph in the brief before an answerer relies
     on it. "I'm good with this" means it SERVES — the same disposition they
     chose for guidance on the fourth docket, and for the same reason: refusing
     throws away a real answer and serving silently throws away the one thing
     the reader needs to know about it.

  2. REVIEWABLE. `Reviewed: open`, and the INVERSE of a citation check.
     Everything else here asks *what proves this*; an uncited position has
     nothing to run that on, and the question that matters about it is *does
     anything on file contradict it*. `ask.review_brief` assembles what a
     reviewer must read. It does not decide — a reading is made by a named party
     quoting words, and for a policy that party is the firm.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import positions                                            # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

THE_POLICY = "SATC policy — unidentified purchases are flagged, not drawn"
THE_OLD_PIN = "26 CFR 1.262-1(a) — the general rule"


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


@pytest.fixture(scope="module")
def policy(desk):
    q = desk.position(THE_POLICY)
    assert q is not None, "the firm's policy is no longer on file"
    return q


# ── the record ──────────────────────────────────────────────────────────────

def test_the_position_is_unpinned_from_the_paragraph_that_did_not_decide_it(desk):
    """The instance, not just the property."""
    assert desk.position(THE_OLD_PIN) is None, (
        "the policy is pinned to § 1.262-1(a) again. Two independent judges "
        "refused that pairing and the firm answered 'Firm policy, no "
        "citation' — if this is deliberate, that decision needs revisiting "
        "rather than this line deleting.")


def test_the_firms_words_did_not_change(policy):
    """WHAT MOVED IS THE CLAIM ABOUT WHAT IT RESTS ON, and nothing else.
    Repinning a position must never become an excuse to reword one."""
    assert policy.position == (
        "flag it for attention and ask the client what was bought; do not book "
        "it to owner draws on the seller's name")
    assert "5 September 2026" in policy.ratified


def test_it_declares_what_it_rests_on(policy):
    assert policy.kind == positions.FIRM_POLICY
    assert policy.is_policy


def test_it_is_marked_as_reviewable(policy):
    """The firm's first condition. `open` is the mark and not a defect."""
    assert policy.reviewed == positions.OPEN
    assert policy.unreviewed


def test_its_reference_cannot_be_read_as_a_paragraph(policy):
    """The danger is not the missing citation — it is a reference a reader takes
    for one. It travels into refusals, briefs and notifications without the
    position attached, so the WORDS have to carry it."""
    assert policy.citation.startswith("SATC policy")
    assert "CFR" not in policy.citation and "Pub." not in policy.citation


def test_every_other_position_is_unaffected(desk):
    """Narrowing. Adding the field changed no existing position: absent means
    `authority`, which is what all twenty were."""
    others = [q for q in desk.positions if not q.is_policy]
    assert len(others) == 19, f"{len(others)} cited positions, not 19"
    for q in others:
        assert q.kind == positions.AUTHORITY
        assert not q.unreviewed
        assert q.reviewed == positions.OPEN, (
            "a cited position records a review it never had")


# ── the guards, each checked by construction ────────────────────────────────

def _broken(tmp_path, old, new):
    dst = tmp_path / "corpus"
    shutil.copytree(CORPUS, dst)
    f = dst / "positions" / "POSITIONS.md"
    text = f.read_text(encoding="utf-8")
    assert old in text, "the fixture's premise moved"
    f.write_text(text.replace(old, new, 1), encoding="utf-8")
    return dst


def test_a_misspelt_kind_refuses_rather_than_defaulting(tmp_path):
    """THE ONE WAY THIS FIELD CAN DO HARM. `Kind: firm polcy` falling back to
    `authority` leaves a position claiming the authority of a paragraph it does
    not rest on — the mis-pin this exists to stop, reintroduced by a typo."""
    d = _broken(tmp_path, "**Kind:** firm policy", "**Kind:** firm polcy")
    with pytest.raises(record.RecordError, match="firm polcy"):
        record.load(d)


def test_a_policy_citing_a_publisher_is_refused(tmp_path):
    """A reference that resolves to a publisher is the mis-pin wearing the label
    that says it is not one — which is the whole failure `dec-pos2` is about,
    since the position it was decided on carried exactly that.

    REFUSED BY THE PREFIX, AND THAT IS WHY THERE IS NO SECOND GUARD. The first
    draft of `record.load` also checked "falls under the policy source and no
    other". It could never fire: a reference beginning `SATC policy —` cannot
    resolve to a publisher unless one registers a prefix beneath it, and the
    uniqueness check refuses a citation matching more than one source anyway. It
    was deleted rather than left reading as protection.
    """
    d = _broken(tmp_path, f"**Citation:** {THE_POLICY}",
                "**Citation:** 26 CFR 1.262-1(a)")
    with pytest.raises(record.RecordError, match="reference must begin"):
        record.load(d)


def test_a_cited_position_may_not_claim_a_review(tmp_path):
    """`Reviewed:` says an UNCITED position was checked against what is on file.
    On a cited one it would read as a general review log and claim something
    nothing here checks."""
    d = _broken(tmp_path,
                "**Citation:** 26 CFR 1.263(a)-1(f)(5) · **Recorded:** 2026-09-05",
                "**Citation:** 26 CFR 1.263(a)-1(f)(5) · **Recorded:** 2026-09-05"
                "\n\n**Reviewed:** looked fine to me")
    with pytest.raises(record.RecordError, match="rests on authority"):
        record.load(d)


def test_a_policy_reference_on_a_position_that_does_not_declare_one_is_refused(
        tmp_path):
    d = _broken(tmp_path, "**Kind:** firm policy\n\n", "")
    with pytest.raises(record.RecordError, match="does not declare"):
        record.load(d)


# ── condition 1 · it serves, and it says what it is ─────────────────────────

def test_it_serves(desk, policy):
    """*"I'm good with this"* — so it answers. Refusing would throw away a real
    answer the firm gave in as many words."""
    out = engine.serve(
        engine.Answer(position=policy.position, citation=policy.citation),
        desk, question="a charge at a store and nobody knows what was bought")
    assert isinstance(out, engine.Served), getattr(out, "detail", out)
    assert out.binding, "the firm is the last layer; their words bind"


def test_the_answer_that_leaves_says_it_rests_on_the_firm(desk, policy):
    out = engine.serve(
        engine.Answer(position=policy.position, citation=policy.citation),
        desk, question="a charge at a store and nobody knows what was bought")
    assert "firm's own standing policy" in out.caveat
    assert "not on any paragraph" in out.caveat
    assert "Nobody has yet checked it" in out.caveat, (
        "an uncited position that nobody has read against the record must say "
        "so — that is the firm's second condition, on the answer itself")


def test_a_cited_answer_carries_no_such_caveat(desk):
    """Narrowing. If every binding answer started explaining itself, the one
    that needs to would stop standing out."""
    q = next(x for x in desk.positions if not x.proposed and not x.is_policy)
    out = engine.serve(engine.Answer(position=q.position, citation=q.citation),
                       desk, question="what is the threshold")
    if isinstance(out, engine.Served):
        assert "standing policy" not in out.caveat


def test_the_brief_marks_it_before_an_answerer_relies_on_it(desk, policy):
    """On the answer is too late to be a disclosure; it has to be where the
    reading happens."""
    text = ask.brief("what was bought", desk.narrowed_to([policy.citation]))
    assert "the firm's own standing policy, not authority" in text
    assert "Nobody has yet read it against what is on file" in text


# ── condition 2 · the inverse check ─────────────────────────────────────────

def test_the_review_finds_the_authority_nearest_the_policys_own_words(policy):
    found = ask.against(policy)
    assert found, "nothing to read against it, so nobody can review it"
    assert all(f.matched for f in found), "a hit with no words shown"


def test_the_query_is_the_position_and_not_a_list_somebody_wrote(policy):
    """A hand-written list of what to check a policy against is written by
    whoever proposed the policy — the preparer verifying their own work."""
    from_words = [f.held.citation for f in ask.against(policy)]
    assert from_words == [
        f.held.citation
        for f in ask.looked(f"{policy.title} {policy.position}")], (
        "the review is scored on something other than the position's own words")


def test_the_review_brief_asks_one_question_and_answers_none(policy):
    text = ask.review_brief(policy)
    assert "Does any of that contradict the position above?" in text
    assert "Nothing is decided here" in text
    for verdict in ("contradicted: yes", "contradicted: no", "no conflict found"):
        assert verdict not in text.lower(), (
            f"the brief reaches a verdict ({verdict!r}); a reading is made by a "
            f"named party quoting words, and for a policy that party is the firm")


def test_the_review_brief_says_which_position_and_quotes_it(policy):
    text = ask.review_brief(policy)
    assert policy.id in text
    assert policy.position in text
    assert "rests on the firm" in text


def test_finding_nothing_is_reported_as_coverage_and_not_as_a_clean_bill():
    """The failure that would be easiest to ship: a policy nothing in the corpus
    speaks to, reported as reviewed and clear."""
    import dataclasses
    empty = dataclasses.replace(
        record.load(CORPUS).positions[0],
        id="POSX", title="zzqx vvbbnn", position="wwbbq zzxrt ppnvk")
    text = ask.review_brief(empty)
    assert "not a clean bill" in text.lower()
    assert "coverage answer, not a review one" in text
