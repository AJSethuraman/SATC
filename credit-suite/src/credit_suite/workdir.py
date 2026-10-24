"""Where the tie-out's working data lives. Declared once, read everywhere.

Fifty-two of the fifty-eight tie-out tools had the same Windows temp path typed
into them, session id and all:

    C:\\Users\\ajish\\AppData\\Local\\Temp\\claude\\C--Users-ajish-SATC
        \\261f7248-3cbc-4aa2-aacf-e4ff9181778a\\scratchpad

Two things were wrong with that and only one of them is tidiness. The folder is
one Windows cleanup away from gone, and it holds **the 760 filed Call Reports
the whole feed was checked against**. Those are not a cache. 442 of the 760
have been amended at least once since the quarter they report, so fetching them
again does not get them back -- the regulator serves whatever is current then.
Losing this folder does not cost an hour of downloading; it costs the ability
to reproduce a tie-out that has already been done.

The firm, 7 September 2026, asked for it on the Forge: *"move to the forge - we
will purge at some point"*. So the location is now a setting rather than a fact
typed into fifty-two files, and moving it again is one line.

**Resolution order**, most explicit first:

1. ``$CREDIT_SUITE_WORKDIR`` -- an env var, for a run that wants somewhere else
2. the Forge, ``SATC-evidence/credit-suite-workdir``
3. the old temp folder, if it is still there -- so a checkout mid-move works
4. refuse, naming all three, rather than inventing an empty directory

Step 4 matters. A missing working folder that silently becomes an empty one
gives every tool nothing to read and every count an honest-looking zero, which
is the shape of the failure this project keeps finding.
"""
from __future__ import annotations

import os
import pathlib

#: The Forge -- outside any git working tree, so `git clean` cannot reach it,
#: and on a disk rather than in a temp folder.
FORGE = pathlib.Path.home() / "SATC-evidence" / "credit-suite-workdir"

#: Where it used to be. Kept so a checkout that has not moved yet still runs,
#: and so the failure message can say where to look.
LEGACY = (pathlib.Path.home() / "AppData" / "Local" / "Temp" / "claude"
          / "C--Users-ajish-SATC"
          / "261f7248-3cbc-4aa2-aacf-e4ff9181778a" / "scratchpad")

ENV = "CREDIT_SUITE_WORKDIR"

#: What must NOT be thrown away in a purge, and why. The firm said they will
#: purge at some point; this is what makes that a safe decision rather than a
#: guess. Everything not named here can be rebuilt from what is.
IRREPLACEABLE = {
    "banks": "the 760 filed Call Reports as the regulator served them on "
             "5-7 September 2026. 442 have been amended since the quarter "
             "they report, so re-fetching gets a different document.",
    "filings": "the machine-readable half of the same 760 filings.",
}
REBUILDABLE = {
    "deepstrips": "colour row photographs, cut from banks/ -- about 12 minutes",
    "deepstrips-grey": "the shrunk copies the exhibits embed -- about 8 minutes",
    "deep": "intermediate pulls; refetched from the FDIC in minutes",
}


def workdir(required: bool = True) -> pathlib.Path:
    """The working folder, or a refusal that says where it looked.

    ``required=False`` returns the preferred location without checking it
    exists -- for a tool that is about to create it.
    """
    override = os.environ.get(ENV)
    if override:
        path = pathlib.Path(override)
        if path.is_dir() or not required:
            return path
        raise SystemExit(
            "%s is set to %s and there is no such directory." % (ENV, path))
    for candidate in (FORGE, LEGACY):
        if candidate.is_dir():
            return candidate
    if not required:
        return FORGE
    raise SystemExit(
        "No working folder. Looked in:\n"
        "  $%s   (not set)\n"
        "  %s   (the Forge, where it belongs)\n"
        "  %s   (where it used to be)\n"
        "This holds the filed Call Reports every check runs against. It is not "
        "a cache: most of those filings have been amended since, so fetching "
        "them again returns different documents. Restore it, or set $%s."
        % (ENV, FORGE, LEGACY, ENV))
