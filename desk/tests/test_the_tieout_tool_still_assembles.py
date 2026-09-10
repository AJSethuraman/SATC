"""The tie-out tool must at least be importable and whole.

WHY THIS EXISTS, and it is a near miss rather than a theory. On 6 September 2026
the comparison functions were moved out of `tools/tieout.py` into `comparing`, so
that `proving` could share them without dragging `ssl` onto the import path. The
extraction took the `Line` dataclass with it — the record every verdict is
returned in — and `check()` was left referring to a name that no longer existed.

THE WHOLE SUITE PASSED. 462 tests, green, with the tie-out tool unable to produce
a single result. Nothing here exercises `check()`, because `check()` fetches and
this desk's conftest replaces the socket layer; so the one tool whose output the
firm is being asked to trust had no test that it assembled at all. It was found
by running it by hand against irs.gov, which is exactly the check that is not
supposed to be the safety net.

WHAT THIS CAN AND CANNOT DO. It cannot fetch, so it cannot tell whether the tool
gets the right answer — the live run is still the only thing that proves that,
and 531 of 533 is still a measurement taken by hand. What it CAN do is fail on
the commit that leaves the tool unable to run: every name `check()` reaches for
exists, `Line` can be built and read, and the parsing that has no network in it
works on real input.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import comparing                                            # noqa: E402
import record                                               # noqa: E402
import tieout                                               # noqa: E402
from conftest import CORPUS                                  # noqa: E402


def test_every_global_check_reaches_for_exists():
    """The exact failure above: `check()` referred to `Line` after `Line` was
    moved out. Reading the function's own bytecode is the only way to catch a
    name error inside a branch no offline test can reach."""
    # `__builtins__` is a DICT inside an imported module and a MODULE inside
    # __main__, so `dir(__builtins__)` there lists dict methods and `Exception`
    # reads as undefined. Import the module by name and the question is exact.
    import builtins

    absent = [n for n in tieout.check.__code__.co_names
              if not hasattr(tieout, n) and not hasattr(builtins, n)]
    # Attribute lookups on locals land in `co_names` too (`source.id`, `got.at`),
    # so this narrows to names that look module-level: capitalised, or private.
    unresolved = [n for n in absent if n[0].isupper() or n.startswith("_")]
    assert not unresolved, (
        f"`check()` reaches for {unresolved}, which `tieout` does not define. "
        f"The tool cannot produce a result, and no offline test runs it.")


def test_the_verdict_record_is_whole():
    fields = {f.name for f in dataclasses.fields(tieout.Line)}
    for needed in ("desk", "citation", "verdict", "how", "matched_chars",
                   "stopped_at", "sha256", "fetched_at", "url"):
        assert needed in fields, f"Line lost {needed!r}"
    line = tieout.Line("d", "c", "S1", "t", "u", 10, tieout.TIED
                       if hasattr(tieout, "TIED") else "TIED")
    assert line.verdict


def test_the_comparison_is_borrowed_and_not_copied():
    """One folding table, one meaning for a marked omission. Two copies would
    disagree within a week and report different verdicts about one passage."""
    assert tieout.normalise is comparing.normalise
    assert tieout.elided_match is comparing.elided_match
    assert tieout.ELLIPSIS is comparing.ELLIPSIS


def test_comparing_reaches_nothing_that_reaches_the_network():
    """The property that let `proving` import it at all. `tools/tieout.py`
    fetches, so importing it pulls in `ssl`, and this suite replaces the socket
    layer — every test of `proving` failed inside `ssl.py` until the comparison
    moved somewhere that imports neither."""
    src = (HERE / "comparing.py").read_text(encoding="utf-8")
    for forbidden in ("import urllib", "import ssl", "import socket",
                      "import http", "import requests", "subprocess"):
        assert forbidden not in src, (
            f"comparing.py reaches {forbidden!r}; anything the engine's front "
            f"door imports must not be able to reach the network")


def test_the_brief_is_parsed_back_out_of_real_text():
    """`brief_passages` is the half of the tool with no network in it, and it is
    the half that decides what goes on the `ours` side of every comparison. A
    citation the brief does not carry is a finding in itself."""
    desk = record.load(CORPUS)
    parsed = tieout.brief_passages(desk)
    assert parsed, "the brief parsed to nothing"
    held = {p.citation for p in desk.passages}
    assert set(parsed) <= held, (
        f"the brief carries citations the record does not: "
        f"{sorted(set(parsed) - held)}")
    # AND THE TEXT IS THE PASSAGE'S, not a summary of it.
    for citation, text in parsed.items():
        stored = desk.passage(citation)
        assert comparing.normalise(text)[:80] == \
            comparing.normalise(stored.text)[:80], citation


def test_the_as_of_date_is_asked_for_rather_than_typed():
    """A verification date in a constant slips, and slipping only ever hides.

    MEASURED 7 SEPTEMBER 2026. `AS_OF` was the literal "2026-01-01", with a
    comment saying eCFR's versioner refuses a future date so January was the
    last date known good. The first half holds — the versioner 404s from about
    five days back. The second was stale: it served 2026-09-01 that day, so the
    corpus was being verified against text eight months older than the newest
    available, and an amendment in between would have tied out clean against a
    superseded version.

    A stale verification date is worse than an absent one. It cannot produce a
    false DIFFERS; it can only fail to produce a true one.
    """
    assert not hasattr(tieout, "AS_OF"), (
        "`AS_OF` is back as a module constant. The date eCFR is asked about "
        "must be asked FOR — `titles.json` carries `latest_issue_date` — or it "
        "goes stale silently and can only ever hide a difference.")
    assert callable(tieout.as_of)
    for fn in (tieout._ecfr_url,):
        assert "as_of" in fn.__code__.co_names, (
            f"{fn.__name__} no longer asks for the as-of date")


def test_the_fallback_exists_and_is_never_silent():
    """Unknown is a third answer here too. If eCFR cannot be asked, the run
    still happens — and says on stderr which date it fell back to, because a
    verification quietly performed against the wrong period is the failure this
    whole change is about."""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", tieout._FALLBACK_AS_OF)
    src = (HERE / "tools" / "tieout.py").read_text(encoding="utf-8")
    body = src.split("def as_of(")[1].split("\ndef ")[0]
    assert "except Exception" in body and "file=sys.stderr" in body, (
        "the fallback is silent; a date that slipped without saying so is "
        "exactly what this replaced")


def test_the_exhibit_generator_still_reaches_a_name_that_exists():
    """The near miss this file was written for, one module over. Renaming
    `AS_OF` left four references in `tieout_exhibit.py` pointing at a name that
    no longer existed, and nothing in the suite runs that generator."""
    import builtins
    import tieout_exhibit as te
    src = (HERE / "tools" / "tieout_exhibit.py").read_text(encoding="utf-8")
    # ATTRIBUTE ACCESS, NOT THE FILENAME. The first version of this matched
    # `tieout.py` written in prose and reported that the module lacks an
    # attribute called `py`. A test whose first failure is its own is one nobody
    # trusts the second time.
    reached = re.findall(r"\btieout\.([A-Za-z_][A-Za-z_0-9]*)\s*[(\.,)\]}]", src)
    assert reached, "the pattern found no attribute access at all"
    for name in set(reached):
        assert hasattr(tieout, name), (
            f"tieout_exhibit reaches `tieout.{name}`, which does not exist")


def test_ecfr_serves_a_section_under_two_url_shapes_and_both_normalise():
    """The searcher is what found the second shape, by fetching one.

    A desk records `/current/title-26/section-1.263(a)-3` because a person typed
    the short form. eCFR's own site links, and a search engine returns, the full
    outline form with the chapter, subchapter, part and subject group in it — and
    the old pattern required `section-` to follow `title-26/` immediately, so the
    outline form fell through to the human page. That page is the JavaScript
    shell this function exists to route around, so the fall-through did not fail
    loudly; it fetched something a plain client cannot read.
    """
    short = tieout._ecfr_url(
        "https://www.ecfr.gov/current/title-26/section-1.263(a)-3")
    outline = tieout._ecfr_url(
        "https://www.ecfr.gov/current/title-26/chapter-I/subchapter-A/part-1/"
        "subject-group-ECFRc4930337f38ecfd/section-1.162-3")
    assert short.endswith("title-26.xml?section=1.263(a)-3")
    assert outline.endswith("title-26.xml?section=1.162-3")
    assert "/api/versioner/" in short and "/api/versioner/" in outline


def test_a_versioner_url_is_still_re_pointed_rather_than_rewritten():
    """The widened pattern must not start matching URLs that are already the
    answer: a versioner url carries `title-26.xml?section=…`, and reading a
    `section-` out of it would build a nested one."""
    again = tieout._ecfr_url(
        "https://www.ecfr.gov/api/versioner/v1/full/2020-01-01/"
        "title-26.xml?section=1.274-12")
    assert again.endswith("title-26.xml?section=1.274-12")
    assert again.count("/full/") == 1 and "2020-01-01" not in again
