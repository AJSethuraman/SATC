"""The declared subject-source map stops gating and starts advising.

WHY IT BLOCKED. `cited_off_source` was allowed to refuse because, on
5 September 2026, `serve()` "had no key and no equivalent of `grade()`'s
citation check" — its own words. A model could cite a real, resolvable, primary
paragraph that did not answer the question, and nothing downstream could tell.

BOTH HALVES OF THAT ARE GONE.

**The check exists now.** #346 built the judge: a second reader handed the
paragraph and the conclusion, asked whether one supports the other, on all seven
desks, on every answer. That reads meaning. The map reads a keyword table.

**And the failure it was built from is on a model we no longer target.** The
firm, 8 September 2026: *"We currently do not need to test against ollama. Stop
trying to. This can be a Claude code only thing that's why the forge - desk
session exists. Ollama is end game."* Every measurement behind the block is
`qwen3:8b`.

WHAT IT COSTS, MEASURED 8 September 2026 over all 98 recorded problems, asking
whether the guard would refuse each desk's OWN recorded citation:

    question phrased as the full fact pattern (~50 words)   0 of 98 refused
    question phrased as its title (~8 words)               10 of 98 refused

**It is measuring how many declared keywords the asker typed, not whether the
paragraph answers the question.** Six of the ten are `vehicle-expense`. And the
suite could never see it: `PROBLEMS.md` is written in the verbose style, which
is the style that scores 0.

Confirmed live the same day. Asked *"How is the depreciation worked out?"* on a
purchased trailer, the guard refused § 1.263(a)-2(d)(1) — the ACQUISITION rule,
the on-point predicate for a thing that was bought — because the word
"depreciation" pinned the subject to the improvements source.

The firm, on the architecture, having said it more than once:

    "it is difficult to have multiple desks that are so silo'd when we can have
     an agent tie things out and provide suggestions."

So the map now WARNS. It still says exactly what it always said — this citation
came from a source this desk does not declare for this subject — and the reader
decides, with the judge standing behind the answer. `DESIGN-PRINCIPLES.md` is
satisfied the same way `straddle` satisfies it: the doubt is stated, above the
conclusion, rather than the answer being withheld.
"""
from __future__ import annotations

from pathlib import Path

import engine
import record
from engine import Answer

DESKS = Path(__file__).resolve().parents[1] / "desks"

#: The measured case. `tool`/`asset` are declared on S1 (§ 1.263(a)-1); the
#: $200 materials-and-supplies line lives in S2 (§ 1.162-3), and the desk's own
#: prose says it answers this "from § 1.263(a)-1(f) and § 1.162-3".
QUESTION = "Where is the line between a tool and a fixed asset?"
OFF_SOURCE = "26 CFR 1.162-3(c)(1)(iv)"


def _serve():
    desk = record.load(DESKS / "capitalization-and-de-minimis")
    return engine.serve(
        Answer(position="a tool costing $200 or less is materials and supplies",
               citation=OFF_SOURCE),
        desk, question=QUESTION)


def test_it_is_served_rather_than_refused():
    out = _serve()
    assert isinstance(out, engine.Served), (
        f"still refused: {getattr(out, 'reason', out)!r} — the declared map is "
        f"advice now, and the judge is the gate")


def test_the_warning_is_carried_and_names_the_declared_sources():
    out = _serve()
    assert out.off_source, "served with no warning at all — the doubt vanished"
    assert "S1" in out.off_source or "declare" in out.off_source.lower()


def test_the_warning_is_read_before_the_conclusion_not_after():
    """The firm's rule, from the straddle note: a warning below the answer is a
    retraction of something already bought. Above it, it is a frame."""
    text = str(_serve())
    assert out_i(text, "not declare") < out_i(text, "materials and supplies"), (
        "the warning prints below the conclusion, which is the placement the "
        "firm already rejected once")


def out_i(text: str, needle: str) -> int:
    i = text.lower().find(needle.lower())
    assert i >= 0, f"{needle!r} is not in the served answer at all"
    return i


def test_an_on_source_citation_carries_no_warning():
    """The note must mean something. If every answer carried it, it is noise."""
    desk = record.load(DESKS / "capitalization-and-de-minimis")
    out = engine.serve(
        Answer(position="the ceiling is $2,500 per invoice or item without an AFS",
               citation='IRS Tangible Property Final Regulations, '
                        '"What is the de minimis safe harbor election?"'),
        desk, question="what is our capitalisation threshold?")
    if isinstance(out, engine.Served):
        assert not out.off_source
