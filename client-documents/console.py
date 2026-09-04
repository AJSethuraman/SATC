"""Making this program's own output printable on the machine it runs on.

Twenty-two modules here draw with characters that are not in **cp1252**, which
is what a default Windows console still encodes to: the rule `─` under every
heading, the `→` in a next-step line, the `←` in the walkthrough, the real minus
`−` the invoice's field doc asks for. On Linux that is nothing; on Windows every
one of them raises `UnicodeEncodeError` at the moment it is printed.

On 3 September 2026 — the first run on the firm's own machine — `exercise.py`
built all 190 documents, opened every one of them in a browser, reported
`0 refusals, 0 with something unexpected`, and then **died printing its own
summary table**, on the `→` in a scenario line. Exit code 1. The work was
finished and correct; the only thing that failed was saying so.

That is the worst shape a failure can take here. A harness that exits 1 after
doing everything right will be read as a harness that found something wrong, and
the run that proved 190 documents render is the run that looks broken.

`errors="replace"` rather than strict: on a console that genuinely cannot draw a
glyph, a `?` in one column still leaves the rest of the report readable. Losing
the box-drawing character is not worth losing the sentence around it.

Call it first thing in any entry point that prints. It is deliberately not done
at import time — a module that reconfigures the interpreter's streams merely
because somebody imported it would be a nasty surprise inside a web request or
another program's test run.
"""

from __future__ import annotations

import sys


def speak_utf8() -> None:
    """Let stdout and stderr carry the characters this program actually uses."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):      # redirected, closed, or replaced
                pass
