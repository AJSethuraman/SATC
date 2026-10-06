"""Canon is findable from BOTH layouts, and these tests are restored.

THEY WERE DELETED BY ACCIDENT, on 8 September 2026. `d7b44a8c` ("delete the
desks. One corpus.") removed `routing.py` and with it `tests/test_routing.py`,
which is where these three happened to be filed. They have nothing to do with
routing: they were added on 4 September by `270ddc6a` ("desk could not find
canon when installed as a plugin"), and one of them —
`test_canon_is_found_in_the_marketplace_cache_layout` — is **the test written
specifically to prove the installed cache layout works.**

Forge-Desk, reading 0.27.0 from the installed plugin on 14 September 2026:
*"That is collateral, not a fix."* They named one; the deletion took three.

WHY LOSING THEM MATTERS MORE THAN LOSING A TEST. `_canon.py`'s own docstring
records the bug they were written for: a sibling lookup from desk resolves to
`<...>/desk/canon`, which never exists once installed, *"and it passed
everything, because the repository is the only place the tests ran, and there
the wrong rule and the right one agree."* Deleting the only checks that run the
other rule puts the codebase back where it was before that was found — with the
fix still in place and nothing holding it there.

ONE CHANGE FROM THE ORIGINALS, and it is named rather than quiet. The cache
fixture wrote canon's REAL `record.py` into it, read from `<repo>/canon`. That
read is itself repository-only, so restoring it verbatim would have rebuilt the
same defect inside the test for it. The fixture writes a stub instead; every
assertion here is about which DIRECTORY `_candidates()` reaches, and a stub
satisfies `record.py.is_file()` exactly as the real file did.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import _canon                                               # noqa: E402


def test_canon_is_found_in_the_marketplace_cache_layout(monkeypatch, tmp_path):
    """The layout the repository never exercises.

    Installed from a marketplace, plugins are cached as
    `<cache>/<marketplace>/<plugin>/<version>` — so canon's root is
    `.../satc/canon/1.4.0` while desk's is `.../satc/desk/0.1.0`. A sibling
    lookup from desk resolves to `.../satc/desk/canon`, which never exists.

    Written sibling-only first and it passed everything, because the repository
    is the only place the tests ran and there both rules agree. Found by opening
    the real plugin cache. The fixture below is built here rather than read from
    this machine, so the test proves the shape rather than the installation.
    """
    cache = tmp_path / "cache" / "satc"
    canon = cache / "canon" / "1.4.0"
    desk = cache / "desk" / "0.1.0"
    canon.mkdir(parents=True)
    desk.mkdir(parents=True)
    (canon / "record.py").write_text("touches = None\n", encoding="utf-8")

    monkeypatch.delenv("CANON_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(desk))
    monkeypatch.setattr(_canon, "__file__", str(desk / "_canon.py"))
    monkeypatch.delitem(sys.modules, "canon_record", raising=False)

    found = [c for c in _canon._candidates() if (c / "record.py").is_file()]
    assert found, (
        "canon is not findable in the marketplace cache layout; a sibling "
        "lookup from desk resolves to .../desk/canon, which never exists"
    )
    assert found[0] == canon


def test_the_newest_installed_version_wins(monkeypatch, tmp_path):
    """Two versions can sit in the cache at once. Take the later one."""
    cache = tmp_path / "cache" / "satc"
    desk = cache / "desk" / "0.1.0"
    desk.mkdir(parents=True)
    for v in ("1.3.0", "1.4.0"):
        d = cache / "canon" / v
        d.mkdir(parents=True)
        (d / "record.py").write_text("touches = None\n", encoding="utf-8")
    monkeypatch.delenv("CANON_ROOT", raising=False)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(desk))
    monkeypatch.setattr(_canon, "__file__", str(desk / "_canon.py"))
    found = [c for c in _canon._candidates() if (c / "record.py").is_file()]
    assert found[0].name == "1.4.0"


def test_canon_resolves_from_wherever_this_suite_is_running():
    """The layout that already worked must keep working — this is how every
    other test in the suite finds canon.

    Restored with its assertion unchanged and its NAME widened: it was
    `test_the_repository_layout_still_resolves`, and run from the installed
    plugin it is the cache layout it proves, not the repository one. Naming it
    for the checkout was how a check about the installed shape came to be filed
    where only the checkout ran it.
    """
    found = [c for c in _canon._candidates() if (c / "record.py").is_file()]
    assert found, (
        "canon is not findable from "
        f"{HERE} — every other test that borrows canon's matcher fails next")
