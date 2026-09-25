"""A decision's recommendation is written like its context and must render like it.

FOUND IN A BROWSER, NOT BY A TEST, which is the whole reason this file exists.
The docket's three cards were generated, the suite was green, and the page opened
in Chromium showing:

    <b>Add plain words.</b> Normalising the spelling is a day's work ...

printed as literal characters. The card template escaped a DECISION's `rec` and
rendered its `context` raw -- two fields written by the same hand, in the same
dict, one line apart in `docket_form.py`, treated differently. A POSITION's
recommendation (`note.rec`, out of the record) was already raw, so the escaped
branch was the only one of the three that could not carry emphasis, and nothing
noticed because every earlier decision happened to be written without any.

WHY THIS IS NOT THE SAME RULE AS THE OUTCOME BLOCKS. `either` texts are pinned
PLAIN by `test_docket_form.py`, deliberately: they are one or two sentences where
a tag earns nothing, and escaping is what stops prose becoming markup. `rec` and
`context` are the argument itself -- paragraphs, quoted phrasings, citations --
and they are already authored as HTML. The fix was to make the odd one out
consistent rather than to strip emphasis out of the recommendation.

WHAT THIS PROVES AND WHAT IT DOES NOT. It reads the template and asserts the two
adjacent fields are interpolated the same way. It does NOT prove a browser
renders them -- no Python test can, because the card is built by JavaScript from
a JSON blob. A browser is still the thing that catches this class, and this test
exists so the fix cannot be silently undone between browsings.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import docket_form as df                                    # noqa: E402


def _card_template() -> str:
    """The JS that builds one card, out of the page the generator writes."""
    page = df.render()
    m = re.search(r"function card\(d\) \{.*?\n\}", page, re.S)
    assert m, "the card template is no longer findable in the rendered page"
    return m.group(0)


def test_a_decisions_recommendation_is_not_escaped():
    """`<b>` in a recommendation must reach the reader as bold, not as text."""
    card = _card_template()
    interp = re.findall(r"\$\{n\.rec \|\| ([^}]+)\}", card)
    assert interp, "the recommendation is no longer interpolated as `n.rec || ...`"
    assert interp == ["d.rec"], (
        "a decision's recommendation is rendered as %r. Wrapped in esc() it "
        "prints its own tags as characters -- which shipped onto the docket of "
        "25 September 2026 and was found by opening the page, not by the suite."
        % interp)


def test_the_recommendation_and_the_context_are_treated_the_same_way():
    """The bug was the INCONSISTENCY, so that is what is pinned.

    Both fields are hand-written HTML in the same row dict. Whichever way they
    are rendered, they have to be rendered alike: a reader cannot be expected to
    know that emphasis works in one paragraph of a card and not the one under it.
    """
    card = _card_template()
    rec = re.search(r"\$\{n\.rec \|\| ([^}]+)\}", card).group(1).strip()
    ctx = re.search(r"\$\{d\.context\}", card)
    assert ctx, "the context is no longer interpolated raw; re-read this test"
    assert "esc(" not in rec, (
        "the context renders markup and the recommendation escapes it. They sit "
        "one line apart and are written by the same hand."
    )


def test_a_recommendation_that_carries_markup_is_actually_on_the_page():
    """The guard is inert unless something on the page would trip it.

    A rule about escaping proves nothing on a docket where every recommendation
    happens to be plain -- which is exactly how this survived until 25 September.
    So this asserts the page HAS such a card, and fails when it stops having one
    rather than passing quietly.
    """
    rich = [r for r in df.items()
            if r["kind"] == "decision" and re.search(r"<[a-z/]", r.get("rec") or "")]
    assert rich, (
        "no decision on this docket writes markup into its recommendation, so "
        "the two tests above are not exercised by anything real. Either a card "
        "should be using emphasis, or this guard has outlived the defect."
    )
