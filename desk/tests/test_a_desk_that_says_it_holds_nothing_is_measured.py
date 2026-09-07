"""An `authority_absent` refusal is the MODEL'S claim about its own record.

THE INCIDENT, 7 September 2026. The meals-and-entertainment desk was asked
whether a streaming subscription is ever a business expense and escalated
`authority_absent`, writing: *"§ 1.274-11's own text is not in this desk's
record."* It is — ten passages of it, including the general disallowance at (a),
the definition of entertainment at (b)(1)(i) and the objective test at
(b)(1)(iii), all printed in the brief the model was answering from.

Nothing caught it and nothing could. The other three `authority_absent`
escalations in that same run were correct, and this one looked identical. Found
by hand, by reading the desk against the claim, and it would have sent a Forge
run searching the internet for authority the desk already held.

SO THE ENGINE REPORTS AND DOES NOT OVERRULE. It can say the desk showed 76
passages, ten of them from the source the model named. It cannot say whether any
of them answered the question — that is the merits, and the merits stay with the
model and with whoever reads the queue. The firm was asked before this was
built, on the eighth docket: **"Build the check"**.
"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ask                                                  # noqa: E402
import engine                                               # noqa: E402
import record                                               # noqa: E402
import unsupported                                          # noqa: E402

MEALS = HERE / "desks" / "meals-and-entertainment"
QUESTION = "Is streaming television ever a business subscription?"


def _escalate(reason, working=""):
    return engine.Answer(position="", citation="", escalated=True,
                         reason=reason, working=working)


@pytest.fixture(scope="module")
def meals():
    return record.load(MEALS)


def test_the_refusal_that_started_this_is_measured_and_the_claim_is_false(meals):
    """The whole point, run against the desk and the words that were written."""
    out = engine.serve(_escalate(
        "authority_absent",
        "§ 1.274-11's own text is not in this desk's record."),
        meals, question=QUESTION)
    assert isinstance(out, engine.Refusal)
    assert out.reason == "authority_absent"
    assert out.showed == len(record.shown(meals))
    assert out.showed > 0

    # THE SOURCE THE MODEL NAMED, counted. A total alone does not falsify a
    # claim about one regulation.
    named = [s for s in meals.sources if s.citation_prefix == "26 CFR 1.274-11"]
    assert named, "the meals desk no longer declares § 1.274-11; rewrite this test"
    assert out.showed_by_source.get(named[0].id, 0) > 0, (
        "the desk holds § 1.274-11 and the refusal does not say so, which is the "
        "whole defect this exists to surface")


def test_the_count_is_what_the_brief_actually_prints(meals):
    """ONE DEFINITION. A number counted from a different set than the brief
    prints is a number about a brief nobody saw."""
    brief = ask.brief(QUESTION, meals)
    out = engine.serve(_escalate("authority_absent"), meals, question=QUESTION)
    printed = brief.split("## The authority", 1)[1].count("\n### ")
    assert out.showed == printed, (
        f"the refusal reports {out.showed} shown; the brief prints {printed}")

    src = (HERE / "ask.py").read_text(encoding="utf-8")
    body = src.split("def brief(")[1].split("\ndef ")[0]
    assert "record.shown(desk)" in body, (
        "the brief iterates its own list again; the engine's count can drift "
        "from what was shown")


def test_the_per_source_counts_add_up_to_the_total(meals):
    out = engine.serve(_escalate("authority_absent"), meals, question=QUESTION)
    assert sum(out.showed_by_source.values()) == out.showed


#: EVERY OTHER ESCALATION. `facts_not_established` is a claim about the CLIENT
#: and `authority_permits_choice` is a reading of authority the desk does hold —
#: counting passages against either prints a number that argues with nothing.
@pytest.mark.parametrize("reason", ["facts_not_established",
                                    "authority_permits_choice"])
def test_only_the_claim_about_the_record_is_measured(meals, reason):
    out = engine.serve(_escalate(reason), meals, question=QUESTION)
    assert out.reason == reason
    assert out.showed == 0
    assert out.showed_by_source == {}


def test_a_desk_that_really_showed_nothing_says_nothing(meals):
    """"0 passages" is a refusal agreeing with itself, not a finding."""
    empty = record.Desk(name=meals.name, sources=meals.sources,
                        passages=(), problems=meals.problems,
                        positions=meals.positions)
    out = engine.serve(_escalate("authority_absent"), empty, question=QUESTION)
    assert out.showed == 0
    entry = unsupported.from_refusal(QUESTION, _escalate("authority_absent"),
                                     out, desk=empty)
    assert entry.showed == ""


def test_the_queue_carries_it_where_somebody_will_read_it(meals):
    """A field the engine sets and the queue drops is a measurement nobody sees.
    The queue is where a refusal is acted on, so it is where a refusal that may
    be false has to be visible."""
    a = _escalate("authority_absent",
                  "§ 1.274-11's own text is not in this desk's record.")
    out = engine.serve(a, meals, question=QUESTION)
    entry = unsupported.from_refusal(QUESTION, a, out, model="m", desk=meals)
    assert entry.showed, "the entry lost the measurement"
    text = entry.render()
    assert "**Desk showed:**" in text
    # NAMED, NOT KEYED. `S2: 10` needs a lookup table the reader does not have.
    assert "1.274-11" in text.split("**Desk showed:**")[1].split("\n")[0]


def test_it_survives_the_round_trip(meals, tmp_path):
    a = _escalate("authority_absent", "nothing on this")
    out = engine.serve(a, meals, question=QUESTION)
    entry = unsupported.from_refusal(QUESTION, a, out, model="m", desk=meals)
    p = tmp_path / "q.md"
    unsupported.append(p, entry)
    back = unsupported.parse(p.read_text(encoding="utf-8"))
    assert len(back) == 1
    assert back[0].showed == entry.showed
