"""What this version of the record actually contains, written down beside it.

WHY THIS EXISTS. C11 was recorded on 4 September 2026 and merged to `main`. The
plugin's manifest was not bumped in that commit, and the marketplace entry was
not bumped in the one that later did. The plugin cache is keyed by the version
the MARKETPLACE declares, so there was nothing new to fetch: every installed
session kept reading a record that stopped at C10, while the repository had
eleven. Nothing failed. Bassy simply could not challenge from a conviction the
firm had given, and no test in this suite could tell.

WHAT THIS CAN AND CANNOT DO, said rather than implied. It CANNOT force anybody
to bump a version -- no test can. What it does is make the omission loud: change
`CONVICTIONS.md` and the suite goes red until the digest here is rewritten, and
the line you rewrite sits directly beside the version number. "Should this be
1.6.0?" then appears in the diff a reviewer is reading, instead of being a thing
nobody thought about.

Regenerate:  python canon/release.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

CANON = Path(__file__).resolve().parent

#: Everything an installed session reads AS THE RECORD. A change to any of these
#: is a change to what Bassy knows, which is what a version is for.
RECORD = (
    "CONVICTIONS.md",
    "TENETS.md",
    "skills/how-we-work/SKILL.md",
    "skills/bassy/SKILL.md",
)

RELEASED = CANON / ".claude-plugin" / "RELEASED.json"


def _content(path: Path) -> bytes:
    """The file's content, with line endings normalised to LF.

    HASHING THE RAW BYTES MADE THE DIGEST DEPEND ON WHO CHECKED OUT. Git converts
    these Markdown files to CRLF on a Windows checkout with `core.autocrlf=true`,
    and nothing in this repository forces LF for them -- so the same commit
    hashed differently on Windows than on Linux, and the check would fail on one
    platform or the other whichever machine wrote the digest. This repository
    builds a Windows desktop binary, so that is not a hypothetical checkout.

    A check whose result depends on the machine running it is not a check.
    """
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def digest(root: Path = CANON) -> str:
    """One hash over the record, in a fixed order so it is reproducible."""
    h = hashlib.sha256()
    for name in RECORD:
        h.update(name.encode("utf-8"))
        h.update(b"\0")
        h.update(_content(root / name))
        h.update(b"\0")
    return h.hexdigest()


def version(root: Path = CANON) -> str:
    manifest = json.loads(
        (root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    return manifest["version"]


def write(root: Path = CANON) -> Path:
    out = root / ".claude-plugin" / "RELEASED.json"
    out.write_text(json.dumps(
        {"version": version(root), "record_sha256": digest(root)},
        indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":                                  # pragma: no cover
    path = write()
    print(f"{path}: {json.loads(path.read_text(encoding='utf-8'))}")
