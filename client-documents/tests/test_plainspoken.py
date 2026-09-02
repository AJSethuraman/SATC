"""Does the software talk to its user, or about itself?

The firm, 2 September 2026, sent a screenshot of the refusal screen and asked:

    like in the attached it says something about the yaml. why would that be in
    our software? what software says stuff like that to its user?

The screen had read: "This is work the firm does not take. firm-settings.yaml
lists it under `hard_no` and the interview schema marks the options
themselves."
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import plainspoken  # noqa: E402


def test_no_browser_screen_names_a_file_a_key_or_a_command():
    bad, examined = plainspoken.findings()
    assert not bad, "\n\n".join(bad)
    # S2: the denominator. This check is one refactor away from examining
    # nothing — the page-builder names it looks for could all be renamed —
    # and "nothing reads wrong" across zero strings is not news.
    assert examined >= 200, (
        f"only {examined} browser strings were examined; the scan has stopped "
        f"finding the pages it is meant to read")


@pytest.mark.parametrize("shipped", [
    # The exact sentence the firm sent back, and one of each other shape.
    "This is work the firm does not take. firm-settings.yaml lists it under "
    "`hard_no` and the interview schema marks the options themselves.",
    "Every figure the engine charges, read from fee-schedule.yaml.",
    "This is what was written down the last time cli.py payments asked.",
    "Adding or dropping one is the registry's business.",
    "Set for you by `cli.py returning`, so you need not answer it.",
])
def test_the_check_would_have_caught_what_shipped(shipped):
    """Check the checker against the real thing, not a synthetic one."""
    import re
    assert any(re.search(pattern, shipped) for pattern, _ in plainspoken.TELLS), (
        f"this shipped to a preparer and the check would let it through:\n"
        f"  {shipped}")


def test_it_does_not_object_to_a_screen_that_reads_well():
    """A check that flags everything is a check nobody keeps. These are the
    replacements actually shipped, and none may trip it."""
    import re
    fine = [
        "This is work you have said the firm does not take on. Nothing was "
        "written — no engagement, no price, no documents.",
        "Every figure the firm charges. Changing one here changes the "
        "estimate, the letters and the website together.",
        "1 of 1 bill(s) outstanding, as of the last time the card processor "
        "was asked.",
        "A shoebox: everything is there, just in no order, and somebody has to "
        "put it in order before the return can be started.",
        "<<LikeThis>> is a blank that fills in with the client's own details "
        "when the letter is written.",
    ]
    for text in fine:
        hit = [why for pattern, why in plainspoken.TELLS
               if re.search(pattern, text)]
        assert not hit, f"{hit} tripped on plain writing:\n  {text}"


def test_a_terminal_command_may_still_name_a_file():
    """The rule is about BROWSER screens. A CLI printing `python cli.py render`
    is the most useful thing it can say — its reader is already at a terminal.
    Widening this check to the CLI would delete that."""
    src = (Path(plainspoken.ROOT) / "cli.py").read_text(encoding="utf-8")
    assert "python cli.py" in src, "the CLI stopped telling people what to run"
    _, examined = plainspoken.findings()
    assert examined < 800, (
        "the scan has grown past the browser and is reading the CLI too")
