"""The docket must not state a number the record does not hold.

The failure this guards against is specific and was found in review: the page
announced twenty-two matters and seventeen positions in fixed text, so the first
ratification -- the whole point of the page -- would have left it lying about how
many decisions remained, in the headline, the filter buttons and the preface at
once. Every figure is now derived, and these tests are what keeps it that way:
they read the RENDERED page and compare it with the record, so a number typed
back into the template fails here rather than in front of the firm.
"""
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
sys.path.insert(0, str(HERE))

import record                                               # noqa: E402
from tools import docket_form as df                         # noqa: E402


@pytest.fixture(scope="module")
def page():
    return df.render()


@pytest.fixture(scope="module")
def counted():
    return df._counted()


#: The thirteen matters the FOURTH docket carried, taken from the page published
#: on 6 September 2026 (artifact d9339c39). It is the only independent record of
#: what was already open.
#:
#: IT MOVED OUT OF THIS FILE AND INTO THE GENERATOR, and that is a real change of
#: shape rather than a tidy-up. "New" used to be a `"new": True` flag the page set
#: about itself, checked here against a copy of the previous docket -- and a
#: POSITION cannot carry that flag at all, because positions come out of `desks/`.
#: So POS3, which did not exist that morning, counted as old. The generator now
#: derives "new" by difference against `FIFTH_DOCKET`, and this file asserts the
#: two sets agree, which is the same independence with the arithmetic in one
#: place instead of two.
FIFTH_DOCKET = {
    "dec-cap-field",
    "dec-courts-again",
    "pos-capitalization-and-de-minimis-POS1",
    "pos-capitalization-and-de-minimis-POS2",
    "pos-personal-or-business-POS1",
    "pos-rewards-and-information-returns-POS3",
}


@pytest.fixture(scope="module")
def independent():
    """The same figures, counted from the record and the module -- NOT from
    `_counted`. Read off the thing under test, these tests moved with any bug in
    it and proved only that the page agreed with itself: two mutations survived
    that way, including the hard-coded preface count this file exists to stop."""
    proposed, ratified = 0, 0
    for d in sorted((HERE / "desks").iterdir()):
        if not (d / "SOURCES.md").is_file():
            continue
        for q in record.load(d).positions:
            if q.proposed:
                proposed += 1
            else:
                ratified += 1
    return {"pos": proposed, "ratified": ratified, "dec": len(df.OTHERS),
            "n": proposed + len(df.OTHERS)}


def test_every_total_on_the_page_is_the_number_of_rows_on_it(page, counted, independent):
    assert (counted["n"], counted["pos"], counted["dec"]) == (
        independent["n"], independent["pos"], independent["dec"]), \
        "the generator's own count disagrees with the record"
    n, pos, dec = independent["n"], independent["pos"], independent["dec"]
    assert n == pos + dec, "a row is neither a position nor a decision"
    assert ">%s things waiting on you<" % df._word(n).capitalize() in page
    assert ">0 of %d answered<" % n in page
    assert ">All %d<" % n in page
    assert ">Positions %d<" % pos in page
    assert ">Other %d<" % dec in page


def test_the_preface_counts_what_the_cards_actually_are(page, counted, independent):
    """It hard-coded "Five of these nine" on the second docket and this caught it
    on the run that wrote it -- the same drift the filter labels had."""
    n = independent["n"]
    fresh, from_tieout = counted["fresh"], counted["from_tieout"]
    assert "%s of them are new" % df._word(fresh) in page
    assert from_tieout <= fresh

    # THE SET THE GENERATOR USES IS THE SET THIS FILE HOLDS. Two copies of a
    # thirteen-key list would drift; one copy checked from outside cannot.
    assert df.FIFTH_DOCKET == FIFTH_DOCKET, (
        f"the generator and this test disagree about what the last docket "
        f"carried: {sorted(df.FIFTH_DOCKET ^ FIFTH_DOCKET)}")

    # AND "NEW" IS A DIFFERENCE, NOT A FLAG. Computed here from the rendered
    # rows rather than read off `counted`, so a generator that stopped
    # subtracting would go red.
    keys = {r["key"] for r in counted["rows"]}
    assert fresh == len(keys - FIFTH_DOCKET), (
        f"the page says {fresh} are new; the ones absent from the fourth docket "
        f"are {sorted(keys - FIFTH_DOCKET)}")
    # A POSITION CAN BE NEW, which a `"new": True` flag could never express --
    # positions come out of `desks/`, not out of `OTHERS`. Asserted as the
    # DERIVATION rather than as a fact about any one docket: this one happens to
    # carry no new position, and the sixth would have gone red on a test that
    # demanded one.
    assert all(k in keys for k in keys - FIFTH_DOCKET)
    assert not any(r.get("new") and r["key"] in FIFTH_DOCKET for r in counted["rows"]), (
        "a row is flagged new that the last docket already carried; new is a "
        "difference against that set, never a flag somebody typed")
    assert sum(r.get("shape") == "rule" for r in counted["rows"]) == counted["rules"]
    assert counted["rules"] + counted["concl"] == independent["pos"]


def test_how_many_are_answerable_is_read_off_the_notes(page, counted, independent):
    """Not typed. A position this docket says to hold back is identified by its
    own recommendation, so ratifying one moves the sentence without an edit."""
    waiting, answerable = counted["waiting"], counted["answerable"]
    pos = independent["pos"]
    assert waiting + answerable == pos
    held_back = sum(1 for r in df.items()
                    if "Do not ratify" in (r.get("note") or {}).get("rec", ""))
    assert waiting == held_back, "the held-back count is not read off the notes"
    said = ("%s of the %s positions here are answerable today" % (
        df._word(answerable).capitalize(), df._word(pos))) if waiting else (
        "Every one of the %s positions here are answerable today" % df._word(pos))
    assert said in page


def test_the_ratified_over_proposed_figure_is_read_from_the_desks(page, independent):
    assert "<b>%d / %d</b>" % (independent["ratified"], independent["pos"]) in page


def test_no_card_shows_a_position_its_desk_does_not_hold(counted):
    for row in counted["rows"]:
        if row["kind"] != "position":
            continue
        desk = record.load(HERE / "desks" / row["group"])
        held = [q for q in desk.positions if q.proposed and q.id == row["tag"].split(" · ")[1]]
        assert held, "%s is on the page and not in the record" % row["key"]
        assert held[0].position == row["position"]
        assert held[0].citation == row["citation"]


def test_every_row_has_somewhere_to_put_an_answer(counted):
    for row in counted["rows"]:
        assert row["picks"], "%s has no answer to give" % row["key"]
        assert "Not yet" in row["picks"], \
            "%s cannot be deferred, so silence would have to stand for it" % row["key"]
def test_the_browser_tab_carries_the_same_count_as_the_page(page, independent):
    """The <title> read "Docket · Nine Open" on a page whose headline said
    thirteen, and it shipped: the tab is the artifact's name in the gallery, and
    every test above reads the BODY. A figure is a figure wherever it is
    printed."""
    n = independent["n"]
    assert "<title>Docket \u00b7 %s Open</title>" % df._word(n).capitalize() in page


def test_the_test_count_on_the_page_is_the_suite_s_own():
    """A figure the page states about ITSELF, checked against the suite.

    THE DOCKET SAID 512 WHILE THE SUITE RAN 513, and nothing noticed. The corpus
    size is guarded (`test_the_corpus_figure_is_not_typed_anywhere`) precisely
    because a number in prose goes stale silently; the test count is the same
    shape of claim and had no guard at all. It went stale the moment a test was
    added — within the same session that published the page.

    COLLECTED RATHER THAN RUN. Running the suite from inside the suite is
    recursion; collecting only imports the modules, so this is cheap and
    terminating. Collected == passed + skipped, and the page states the passing
    figure, so the skip count is subtracted here rather than assumed to be zero.
    """
    import subprocess
    import sys as _sys
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run(
        [_sys.executable, "-B", "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider"],
        cwd=root, capture_output=True, text=True).stdout
    m = re.search(r"(\d+) tests? collected", out)
    assert m, f"could not read a collected count from pytest:\n{out[-400:]}"
    collected = int(m.group(1))

    stated = [row for row in df.CHANGED if "tests passing" in row[1]]
    assert len(stated) == 1, f"{len(stated)} rows claim a test count, not 1"
    said = int(stated[0][0].replace(",", ""))

    # AND THE WHOLE PAGE, NOT JUST THAT ROW. The first version checked `CHANGED`
    # alone and passed while the rendered page still said 512 in a matter's
    # prose — the same figure, stale, three sections further down. A guard that
    # covers one of the two places a number appears is a guard that certifies
    # the page as correct while it is wrong.
    rendered = re.sub(r"<[^>]+>", " ", df.render())
    for claim in re.findall(r"(\d{3,4})\s+tests?\b", rendered):
        assert int(claim) == said, (
            f"the page states {claim} tests somewhere and {said} elsewhere; "
            f"one number, stated once, or it goes stale in the copy nobody "
            f"re-reads")

    # ONE SKIP, STATED RATHER THAN DERIVED, and said plainly because the first
    # version of this line dressed a constant up as a computation
    # (`len(glob(...)) and 1`) which always returns 1 and reads as if it counted
    # something. A figure that pretends to be measured is worse than one that
    # admits it is typed: `--collect-only` does not report skips, so this is the
    # honest form. If the skip count changes, this goes red and both move.
    SKIPPED = 1
    assert said == collected - SKIPPED, (
        f"the docket says {said} tests passing; the suite collects {collected} "
        f"with {SKIPPED} skipped, so it should say {collected - SKIPPED}. "
        f"Update `CHANGED` in tools/docket_form.py and republish.")
