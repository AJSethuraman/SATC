"""The two fetch scripts must ask for the same forms.

`corpus/blanks/` ships fetch.sh and fetch.ps1 -- the firm works on Windows
without Git Bash, so the PowerShell one is the one that will actually be run.
Two scripts, two copies of the same list of fifteen forms.

That is the shape this repository keeps paying for: a statement in one place, the
same statement in another, and nothing comparing them. Here the drift would be
quiet and OS-shaped -- somebody adds a form to the script they use, and the
corpus differs depending on who built it. This is the comparison.

It is a runtime check rather than a structural one because there is no cheap
structural fix: a shared list file would have to be read by a bash script, a
PowerShell script and this test, which is three readers of a fourth file to
prevent a drift between two.
"""

from __future__ import annotations

import re
from pathlib import Path

BLANKS = Path(__file__).resolve().parents[1] / "corpus" / "blanks"


def _sh_forms() -> list[str]:
    """Split on the array's CLOSING PAREN AT THE START OF A LINE, not the first
    `)` anywhere.

    The first draft of this split on `)` and silently lost the last two forms,
    because a comment in the array reads `# K-1 (1065) Partner's Share`. It
    reported a drift between the two scripts that did not exist. Worth the note:
    a checker that fails for the wrong reason costs more than no checker, since
    the next person spends their time on a phantom.
    """
    body = (BLANKS / "fetch.sh").read_text()
    block = body.split("FORMS=(", 1)[1].split("\n)", 1)[0]
    return [m.group(1) for m in re.finditer(r"^\s*(\w+)", block, re.M)]


def _ps_forms() -> list[str]:
    body = (BLANKS / "fetch.ps1").read_text()
    block = body.split("[ordered]@{", 1)[1].split("\n}", 1)[0]
    return [m.group(1) for m in re.finditer(r"^\s*'([\w]+)'\s*=", block, re.M)]


def test_both_scripts_exist():
    """The PowerShell one is not optional: it is the one that gets run."""
    assert (BLANKS / "fetch.sh").exists()
    assert (BLANKS / "fetch.ps1").exists()


def test_the_two_scripts_ask_for_the_same_forms():
    sh, ps = _sh_forms(), _ps_forms()
    assert sh, "could not parse the form list out of fetch.sh"
    assert ps, "could not parse the form list out of fetch.ps1"
    assert sh == ps, (
        f"the fetchers have drifted.\n"
        f"  only in fetch.sh : {sorted(set(sh) - set(ps))}\n"
        f"  only in fetch.ps1: {sorted(set(ps) - set(sh))}")


def test_the_readme_lists_every_form_the_scripts_fetch():
    """The README offers the same forms as clickable links, for anyone who would
    rather not run a script at all. A third copy, so a third comparison."""
    readme = (BLANKS / "fetch.sh").parent.joinpath("README.md").read_text()
    for form in _sh_forms():
        assert f"{form}.pdf" in readme, f"{form} is fetched but not linked in the README"


def test_the_powershell_script_says_it_was_never_run():
    """S28, and it is load-bearing here rather than decorative: there is no
    PowerShell in the environment this was written in, so unlike its bash twin
    the .ps1 has never been executed. A reader must not have to guess which of
    the two was proven."""
    text = (BLANKS / "fetch.ps1").read_text().lower()
    assert "never been executed" in text or "not run by its author" in text
