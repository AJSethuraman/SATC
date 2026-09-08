"""The most dangerous served answer told its reader the one thing that was false.

FOUND BY THE DESK, 8 September 2026, measuring whether demoting the source-level
map was safe. It printed this, verbatim:

     1| THIS DESK DOES NOT DECLARE THAT SOURCE FOR THIS SUBJECT, and the ...
     3| a reconciling item, no entry in the books
     5|     26 CFR 1.446-1(a)(4)
     8| Nobody checked that this paragraph says this — only that the citation
        resolves and the source is one this desk uses here.

on an answer carrying `judged=True` — a named second reader HAD looked at the
paragraph and said it carries the conclusion. The desk:

    "As it stands the most dangerous served answer in this whole set — wrong
     citation, affirmative judgment, off-source warning — tells its reader that
     nobody checked, which is the one claim in it that is not true."

WHY IT HAPPENS. `unchecked` is composed inside `serve()`, and `serve()` has no
`judged` parameter — the judgment is attached one layer up by `ask.answer`,
after the sentence is already baked. So the text could never know.

WHY IT MATTERS MORE THAN A WORDING SLIP. This is exactly the answer a reader
most needs to look at: off-source, and standing only on somebody's yes. Telling
them nobody checked sends them to verify it themselves, which is right — but it
also hides that a second reader already said yes and WHO, which is the thing
they would weigh. And when the sentence is wrong here, the reader learns the
sentence is not to be trusted anywhere.
"""
from __future__ import annotations

import engine
import judging


def _served(judged):
    return str(engine.Served(
        position="a reconciling item, no entry in the books",
        citation="26 CFR 1.446-1(a)(4)",
        tier="primary", checked="2026-09-05", binding=True, judged=judged,
        unchecked=("Nobody checked that this paragraph says this — only that "
                   "the citation resolves and the source is one this desk uses "
                   "here. Read the passage below.")))


def _read(verdict):
    return judging.Read(verdict=verdict, by="forge second reader",
                        because="must maintain such accounting records",
                        against="this desk's stored passage")


def test_an_unjudged_answer_still_says_nobody_checked():
    """The sentence is right when it is true, and must not be lost."""
    assert "Nobody checked" in _served(None)


def test_a_judged_answer_does_not_claim_nobody_checked():
    out = _served(_read(judging.HOLDS))
    assert "Nobody checked" not in out, (
        "a second reader looked and said yes; this tells the reader otherwise, "
        "on the one answer in the set that most needs looking at")


def test_a_judged_answer_names_who_read_it():
    out = _served(_read(judging.HOLDS))
    assert "forge second reader" in out, (
        "whose yes it is, is the thing a reader would weigh")


def test_a_judged_answer_still_sends_the_reader_to_the_passage():
    """Replacing the warning with a reassurance would be worse than the bug."""
    out = _served(_read(judging.HOLDS))
    assert "passage" in out.lower(), (
        "a judgment is one reader's yes, not a verification — the reader must "
        "still be sent to the paragraph")
