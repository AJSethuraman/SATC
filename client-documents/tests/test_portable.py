"""Date formats that only work on one operating system.

`%-d` — the day of the month with no leading zero — is a **glibc extension**.
It is not in the C standard and Microsoft's CRT does not have it, so
`strftime("%B %-d, %Y")` returns `September 3, 2026` on Linux and raises
`ValueError: Invalid format string` on Windows.

For about a year that cost nothing, because this suite only ever ran in a Linux
container. On 3 September 2026 it ran on the firm's own Windows machine for the
first time and several hundred tests errored at once — every test that dated a
letter, an estimate or an invoice. Eight call sites across seven modules.

The repair was `dates.py`, which builds the day out of `.day` (an `int`, no
padding, no platform). This test is here because the repair is easy to undo by
accident: `%-d` is what a person reaches for, it reads correctly, and it will
pass every check on the machine of whoever writes it next.

Scanning the source rather than calling the functions is deliberate. A test
that formatted a date would only prove the platform it ran on, which is exactly
the assumption that produced the bug.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The padding modifier, on any conversion that takes one. Written as a class
# rather than `%-d` alone so that `%-m` and `%-I` are caught the first time
# somebody writes one, rather than after the next Windows run.
POSIX_ONLY = re.compile(r"%-[a-zA-Z]")

# `dates.py` names the directive in its own docstring, to say why it is banned.
ALLOWED = {"dates.py"}


def _sources():
    for path in sorted(ROOT.glob("*.py")):
        if path.name not in ALLOWED:
            yield path


def test_no_module_formats_a_date_with_a_glibc_only_directive():
    offenders = {}
    for path in _sources():
        hits = [
            f"{path.name}:{n}: {line.strip()}"
            for n, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1)
            if POSIX_ONLY.search(line)
        ]
        if hits:
            offenders[path.name] = hits

    assert not offenders, (
        "These use a strftime directive that raises ValueError on Windows.\n"
        "Use dates.long_date / dates.day_month / dates.weekday_day_month:\n  "
        + "\n  ".join(h for hits in offenders.values() for h in hits))


def test_the_helpers_produce_the_string_the_documents_expect():
    """The formats the call sites used, pinned to what they used to render."""
    import sys
    sys.path.insert(0, str(ROOT))
    import dates
    from datetime import date

    d = date(2026, 9, 3)                    # a single-digit day: the whole point
    assert dates.long_date(d) == "September 3, 2026"
    assert dates.day_month(d) == "3 September"
    assert dates.weekday_day_month(d) == "Thursday 3 September"

    wide = date(2026, 9, 30)                # and a two-digit one still reads right
    assert dates.long_date(wide) == "September 30, 2026"


# ---------------------------------------------------------------------------
# The other half of the same story: characters this code draws with that a
# default Windows console cannot encode.


def test_the_entry_points_prepare_their_output_before_they_print():
    """`exercise.py` did all 190 documents and then died on its own summary.

    Source-checked rather than run, for the same reason as above: on Linux
    every one of these characters prints fine, so a test that merely printed
    one would pass on the machine where the bug does not exist.
    """
    for name in ("cli.py", "exercise.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        assert "console.speak_utf8()" in src, (
            f"{name} prints, so it has to call console.speak_utf8() first")


def test_the_characters_these_modules_draw_with_survive_a_cp1252_console():
    """Reproduce the Windows console anywhere, by forcing its encoding.

    `PYTHONIOENCODING=cp1252` gives a Linux CI box exactly the stdout that
    broke this, so the check is real off Windows too. Without
    `console.speak_utf8()` this raises `UnicodeEncodeError` and returns 1.
    """
    import os
    import subprocess
    import sys

    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    # The four that are not in cp1252: the rule, the two arrows, the real minus.
    done = subprocess.run(
        [sys.executable, "-c",
         "import console; console.speak_utf8(); print('\u2500\u2192\u2190\u2212')"],
        cwd=ROOT, env=env, capture_output=True, text=True)

    assert done.returncode == 0, (
        f"a cp1252 console still kills this: {done.stderr.strip()}")
