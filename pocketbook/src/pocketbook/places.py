"""Where the tool keeps its own files on the machine that runs it: the memory, the launcher's
last choices and the last error. Standard library only, so the launcher can ask before any
add-on is known to be there.

The tool was called the Origination Cube until 27 Sep 2026 (Goal 3 item 1), and kept these in
~/.origination-cube. A machine that ran it then still has them there, so a file the new folder
does not have yet is read from the old one. Anything written goes to the new folder; the old
file is left as it was.
"""

from __future__ import annotations

from pathlib import Path

#: the tool's folder under the home directory, and the one it used before the rename (still read)
FOLDER, OLD_FOLDER = ".pocketbook", ".origination-cube"


def folder() -> Path:
    """The tool's own folder in the home directory: anything it keeps is written here."""
    return Path.home() / FOLDER


def kept(name: str) -> Path:
    """The kept file NAME, to read: in the tool's folder, or in the old folder when only that one has it."""
    new, old = folder() / name, Path.home() / OLD_FOLDER / name
    return old if not new.exists() and old.exists() else new
