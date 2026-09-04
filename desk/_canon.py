"""Locate canon and borrow its one matching rule.

WHY IMPORT RATHER THAN COPY. Canon's `touches()` carries this note:

    Whole words only. THE ONLY MATCHING RULE IN THIS CODEBASE. Substring
    matching made "extension" fire on "extensive", "rate" on "generate", and --
    in the miner, on its first run -- "refuse" on four pasted terminal
    transcripts saying "refused". [...] It lives in `record.py` rather than in
    each caller because it was briefly written twice, once whole-word and once
    not, and the two disagreed for a day without anything comparing them.

Copying it here would be writing it a third time. `desk` declares canon as a
dependency in its manifest; this is what makes that declaration real rather than
decorative.

WHY IT RAISES INSTEAD OF FALLING BACK. A quiet reimplementation is exactly the
failure the note describes -- two rules that agree until they do not, with
nothing comparing them. If canon cannot be found, that is a broken install and
it should say so, not limp.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


class CanonMissing(RuntimeError):
    """The declared dependency is not there. A broken install, not a fallback."""


def _candidates() -> list[Path]:
    """Everywhere canon can legitimately be, in the order to try.

    TWO LAYOUTS, AND ONLY ONE OF THEM IS OBVIOUS. In the repository, canon is a
    sibling folder: `<repo>/canon`. **Installed from a marketplace it is not** --
    the cache nests a version directory under each plugin, so canon's root is
    `<cache>/<marketplace>/canon/<version>` while desk's is
    `<cache>/<marketplace>/desk/<version>`. A sibling lookup from desk's own
    directory resolves to `<...>/desk/canon`, which never exists.

    Written sibling-only first, and it passed everything: the repository is the
    only place the tests ran, and there the wrong rule and the right one agree.
    It was found by opening the installed plugin cache rather than by a test --
    which is why there is now a test for the installed shape too, built from a
    fixture rather than from whatever this machine happens to have.
    """
    here = Path(__file__).resolve().parent
    roots = [here]
    if env := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        roots.append(Path(env).resolve())

    out = []
    if env := os.environ.get("CANON_ROOT"):
        out.append(Path(env))
    for root in roots:
        # Repository: a sibling folder.
        out.append(root.parent / "canon")
        # Marketplace cache: ../../canon/<version>. Newest version first, so a
        # machine holding two installed versions uses the later one.
        peer = root.parent.parent / "canon"
        if peer.is_dir():
            out.extend(sorted((d for d in peer.iterdir() if d.is_dir()),
                              reverse=True))
    return out


def load_record():
    """Import canon's `record` module from wherever canon actually is."""
    tried = []
    for base in _candidates():
        path = base / "record.py"
        tried.append(str(path))
        if not path.is_file():
            continue
        if (cached := sys.modules.get("canon_record")) is not None:
            return cached
        spec = importlib.util.spec_from_file_location("canon_record", path)
        module = importlib.util.module_from_spec(spec)
        # Registered BEFORE exec: @dataclass resolves a class's __module__
        # through sys.modules, and on an unregistered module that lookup returns
        # None and the import dies inside dataclasses with an AttributeError
        # naming neither canon nor this file.
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[spec.name]
            raise
        return module
    raise CanonMissing(
        "desk declares canon as a dependency and cannot find it. Looked in:\n  "
        + "\n  ".join(tried)
        + "\nSet CANON_ROOT, or install canon@satc."
    )


def touches(text: str, term: str) -> bool:
    """Canon's rule, not a copy of it. Whole words only."""
    return load_record().touches(text, term)
