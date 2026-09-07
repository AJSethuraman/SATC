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

#: WHAT IS HASHED: everything the plugin ships, minus a short list of exclusions
#: each carrying its reason. Written first as four Markdown files called "the
#: record" -- and that was wrong in the way this whole session kept being wrong.
#: `skills/bassy/SKILL.md` invokes `${CLAUDE_PLUGIN_ROOT}/record.py`, and
#: `canon-adopt` invokes `adopt.py`; a change to either ships as installed
#: BEHAVIOUR. Hashing only the prose meant a stale install of the CODE was
#: exactly as invisible as the stale convictions this file was written to catch.
#:
#: So the default is everything, and narrowing it takes a stated reason. A
#: check that has to be told what to look at will always be told too little.
EXCLUDED = (
    # Not installed behaviour. A test edit should not raise "should this be
    # 1.7.0?" -- nothing a session reads has moved.
    "tests",
    # Generated.
    "__pycache__",
    ".pytest_cache",
    # VCS METADATA, BECAUSE CANON IS BUILT TO BE LIFTED OUT. `README.md` says so,
    # and at the root of its own repository this walk reached `.git` and died on
    # the first binary object -- UnicodeDecodeError, in the one layout the plugin
    # exists to support. Even text-only metadata would have moved the digest on
    # every commit.
    ".git",
)

#: Not excluded, REWRITTEN. `plugin.json` ships, so `description`, `author` and
#: `homepage` are installed content and belong in the hash -- excluding the whole
#: `.claude-plugin` directory to keep the version out took the rest with it, and
#: opened a fresh gap of exactly the kind this file closes. Only the version is
#: dropped, because the digest describes content and a bump must not look like
#: one.
MANIFEST = ".claude-plugin/plugin.json"

#: The digest cannot hash the file it is written into.
SELF = ".claude-plugin/RELEASED.json"


def _key(rel: Path) -> str:
    """The order files are hashed in, decided by the path text and nothing else.

    SORTING `Path` OBJECTS SORTED DIFFERENTLY ON EACH PLATFORM. `WindowsPath`
    compares case-insensitively -- that is what the filesystem does, so it is
    what pathlib does -- and `PosixPath` compares byte for byte. So on Windows
    `adopt.py` came before `CONVICTIONS.md`, and on Linux every capitalised name
    came first. The digest hashes the path alongside its content, so the same
    commit hashed two ways, and canon 1.10.0 shipped with `main` red: the number
    written on the Windows box that cut the release could never be reproduced by
    the runner that checked it.

    `_content` already fixed this once for line endings, with the same sentence
    that applies here: a check whose result depends on the machine running it is
    not a check. Line endings were the half that was noticed.
    """
    return str(rel).replace("\\", "/")


def files(root: Path = CANON) -> list[Path]:
    """Every shipped file, sorted, so the hash is reproducible."""
    out = []
    for path in sorted(root.rglob("*"), key=lambda p: _key(p.relative_to(root))):
        rel = path.relative_to(root)
        if not path.is_file() or path.suffix == ".pyc":
            continue
        if any(part in EXCLUDED for part in rel.parts):
            continue
        if _key(rel) == SELF:
            continue
        out.append(rel)
    return out


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


def _hashable(root: Path, rel: Path) -> bytes:
    """What goes into the hash for one file.

    The manifest is canonicalised with its VERSION REMOVED: everything else in it
    ships and is installed content, but the version is the label this digest sits
    beside, and hashing it would make a bump look identical to a change.
    """
    path = root / rel
    if _key(rel) != MANIFEST:
        return _content(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.pop("version", None)
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(root: Path = CANON) -> str:
    """One hash over the record, in a fixed order so it is reproducible."""
    h = hashlib.sha256()
    for rel in files(root):
        h.update(_key(rel).encode("utf-8"))
        h.update(b"\0")
        h.update(_hashable(root, rel))
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
