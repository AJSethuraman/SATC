"""Nothing recognised the question, so nothing fetches on its behalf.

`dec-gate`, 10 September 2026 — the firm: **"Fail closed."**

THE DEFECT, AND IT IS ONE FALSY OBJECT. `candidates.consider` checks that a
publisher is competent to settle a question before fetching from it, and the
check reads `if verdict and url and not domains.governs(...)`. `Verdict` is
falsy when no domain fired, so **a question the map does not recognise skipped
the gate entirely** and went straight to a live fetch of an unrecorded
publisher. The one class where nobody had established that the publisher gets
to say anything was the one class that was never asked.

`domains.Verdict`'s own docstring says a blank verdict is *"a refusal and not an
absence of opinion"*. Two files away it was read as an absence of opinion, which
is what a falsy object invites — and the fix is not to make it truthy but to
have the caller ask the question the docstring already answers.

NOT A NEW POLICY. The firm signed off four dispositions in August: primary
serves silent, secondary serves marked and notifies, tertiary parks and
notifies, and **unknown parks and notifies, because unknown is a real fourth
state**. This is that fourth one reaching the file it was never wired into.

WHAT IT COSTS, MEASURED HERE RATHER THAN ESTIMATED, on the working vernacular of
a close: `test_the_cost_is_measured` counts how many of those questions the map
does not recognise. Forge-Occam reported 9 of 18 on their own close, and the
questions that reach nothing agree exactly with the ones measured here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import candidates                                           # noqa: E402
import domains                                              # noqa: E402
import engine                                               # noqa: E402
import record                                               # noqa: E402
from conftest import CORPUS                                 # noqa: E402

#: A publisher nothing in the record has admitted, on a host the map does not
#: register. Both halves matter: an admitted source would be refused for a
#: different reason, and a registered host would be checked against a domain.
SOMEWHERE = "https://accounting-answers.example/how-to-book-it"

#: THE WORKING VERNACULAR OF A CLOSE, verbatim from
#: `docs/POOL-VS-ROUTING-2026-09-10.md`. Not invented for this file: the last
#: time a check here was built from imagined phrasings, the vocabulary was
#: widened by nineteen words to satisfy sentences nobody had typed.
WORKING = [
    "what records are required for a charge with only a vendor name?",
    "charge on the bank statement with no receipt or invoice - what records are required?",
    "we do not know what was bought - can we deduct it?",
    "the client took cash out of the ATM and we do not know what for",
    "is a payment to a credit card we have no statement for a business cost?",
    "unlabelled deposits into the business account - are they all revenue?",
    "the owner paid the company card from a personal account, what is that?",
    "a cheque with no payee on the feed - how do we book it?",
    "hand tools bought for the trade - deducted or capitalized?",
    "beer at a taproom with a customer - is it deductible?",
    "mileage or actual expenses for the van?",
    "cash back on the business card - income?",
    "what supporting documents does the client have to keep?",
    "the statement cycle closes on the 2nd, what is the opening balance at 1 January?",
    "groceries on the business card - business or personal?",
]


class _Transport:
    """A transport that RAISES. The whole claim is that nothing is fetched, and
    a stub returning a page would let a fetch pass unnoticed."""

    def __init__(self):
        self.asked = []

    def __call__(self, *args):
        self.asked.append(args)
        raise AssertionError(
            "a page was fetched for a question nothing classified")


@pytest.fixture(scope="module")
def desk():
    return record.load(CORPUS)


def _unclassified() -> str:
    """A real question the map does not recognise, found rather than invented."""
    for question in WORKING:
        if not domains.classify(question):
            return question
    raise AssertionError(
        "every working question classifies now, so there is nothing for this "
        "gate to be true of. That is a finding about DOMAINS.md, not a reason "
        "to construct a fake question — delete this file and say so.")


# ── the gate ────────────────────────────────────────────────────────────────

def test_a_question_nothing_classifies_is_refused_before_any_fetch(desk):
    transport = _Transport()
    out = candidates.consider(
        question=_unclassified(), position="it is deductible",
        citation="Some Guide, chapter 4", url=SOMEWHERE,
        text="the words the answerer rests on", desk=desk, transport=transport)

    assert isinstance(out, engine.Refusal), "it fetched instead of refusing"
    assert out.reason == "body_of_authority_unknown"
    assert transport.asked == [], "the refusal came AFTER a fetch"


def test_the_refusal_says_what_would_settle_it(desk):
    """A refusal that names a gap and not the question is a dead end wearing a
    reason code. This one is parked for the firm, and their answer is what adds
    the word the map was missing."""
    out = candidates.consider(
        question=_unclassified(), position="x", citation="Some Guide, chapter 4",
        url=SOMEWHERE, text="words", desk=desk, transport=_Transport())
    assert out.ask.strip(), "parked with nothing for the firm to answer"
    assert "body of authority" in out.ask
    assert "prove nothing" in out.detail, (
        "the detail must say why fetching would not have helped, or this reads "
        "as a transport failure")


def test_a_question_the_map_does_know_is_untouched(desk):
    """The other half. This gate must not become a blanket refusal by the back
    door — that would stop the searcher working at all, and the searcher is the
    thing `dec-books` is about: *it goes and looks*."""
    question = next(q for q in WORKING if domains.classify(q))
    verdict = domains.classify(question)
    url = f"https://{verdict.domain.publishes[0]}/some/page"
    assert domains.governs(url, verdict.domain), "the fixture's premise moved"

    fetched = []

    def transport(*args):
        fetched.append(args)
        raise RuntimeError("far enough: the gate let it through")

    out = candidates.consider(
        question=question, position="x", citation="26 CFR 9.9(z)",
        url=url, text="words", desk=desk, transport=transport)
    assert fetched, "the gate refused a question the map recognises"
    # It refuses in the end — the stub transport raises — but AFTER trying, and
    # for the attempt rather than for the classification.
    assert isinstance(out, engine.Refusal)
    assert out.reason != "body_of_authority_unknown"


def test_a_caller_with_no_question_at_all_is_not_failed_closed(desk):
    """`consider` is called with `question=""` where there is no question to
    classify. Refusing those would fail closed on a case that was never open,
    and would break every caller that has a citation and no sentence."""
    fetched = []

    def transport(*args):
        fetched.append(args)
        raise RuntimeError("the publisher is unreachable, which is not this gate")

    out = candidates.consider(
        question="", position="x", citation="c", url=SOMEWHERE,
        text="words", desk=desk, transport=transport)
    assert fetched, "it refused without trying"
    # It still refuses — nothing was proved — but for the RIGHT reason: the
    # publisher could not be reached, not that the map failed to recognise a
    # question nobody asked.
    assert isinstance(out, engine.Refusal)
    assert out.reason != "body_of_authority_unknown", (
        "a caller with no question was failed closed on the classification of "
        "a question it never made")


# ── the cost, measured rather than estimated ────────────────────────────────

#: HOW MANY OF THE FIFTEEN THE MAP DOES NOT RECOGNISE. Measured 10 September
#: 2026 at desk 0.22.0. Forge-Occam reported 9 of 18 on their own close, and the
#: questions that reach nothing agree exactly.
#:
#: THE DOCKET SAID 8 AND THE MEASUREMENT SAYS 12. The reconciliation was owed
#: and has now been run, against the three revisions of `DOMAINS.md` that this
#: window contains — the same fifteen questions, the map swapped underneath:
#:
#:     e074497b   before the income-side narrowing      9 of 15
#:     810e5dcb   the narrowing itself                 13 of 15
#:     HEAD       plus the `deduct` fix                12 of 15
#:
#: So the narrowing IS what moves this number, and sharply (9 -> 13), and the
#: `deduct` fix gives one back. What is now established is the part that was
#: guessed at before: **no revision in this window produces 8.** The docket's
#: figure is not explained by the narrowing and is not explained at all —
#: recorded as unaccounted for rather than rounded into the story that fits.
#:
#: THIS NUMBER SHOULD FALL, and the mechanism above is what makes it fall: every
#: parked question the firm settles is a word `DOMAINS.md` did not have. If it
#: RISES, something was removed from the map.
UNCLASSIFIED = 12


def test_the_cost_is_measured_and_does_not_go_stale():
    """A figure in prose goes stale silently, which is why it is recomputed."""
    missed = [q for q in WORKING if not domains.classify(q)]
    assert len(missed) == UNCLASSIFIED, (
        f"{len(missed)} of {len(WORKING)} working questions classify nothing, "
        f"and this file says {UNCLASSIFIED}. Down is the map learning a word — "
        f"move the figure. Up is a word having been removed from it.\n  "
        + "\n  ".join(missed))
